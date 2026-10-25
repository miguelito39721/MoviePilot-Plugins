"""音乐重复文件检测：按文件内容与曲目身份分组，只做盘点，不移动或删除文件。

引擎把扫描到的音频路径与标签读取回调传进来，本模块只返回分组结果，
所有搬移动作由引擎在用户明确选择后执行，便于测试与复用。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

# 分块哈希读取的首尾字节数；同一大小的文件才需要计算
_HASH_CHUNK = 256 * 1024
# 同一曲目允许的时长误差（秒），用于容忍不同转码的取整差异
_DURATION_TOLERANCE = 2
# 支持的重复检测方式
DUPLICATE_MODES = ("exact", "same_track")


def _normalize(value: Any) -> str:
    """归一化标题与艺人，忽略大小写、标点与括号补充说明。"""
    text = str(value or "").strip().casefold()
    text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text


def _quick_hash(path: Path, size: int) -> Optional[str]:
    """按文件大小选择整段或首尾分块哈希，避免读取大文件全文。"""
    digest = hashlib.sha1()
    try:
        with path.open("rb") as handle:
            if size <= _HASH_CHUNK * 2:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            else:
                digest.update(handle.read(_HASH_CHUNK))
                handle.seek(size - _HASH_CHUNK)
                digest.update(handle.read(_HASH_CHUNK))
    except OSError:
        return None
    digest.update(str(size).encode())
    return digest.hexdigest()


def _lossless_flag(meta: Any) -> bool:
    """读取元数据的无损标记，未知时按扩展名兜底。"""
    value = getattr(meta, "audio_lossless", None)
    if isinstance(value, bool):
        return value
    return False


def _bitrate(meta: Any) -> int:
    """读取码率用于挑选需保留的最佳副本，未知时为 0。"""
    try:
        return int(getattr(meta, "bitrate", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _duration(meta: Any) -> Optional[int]:
    """读取时长（秒），未知时为 None。"""
    try:
        seconds = float(getattr(meta, "duration", 0) or 0)
    except (TypeError, ValueError):
        return None
    return int(round(seconds)) if seconds > 0 else None


def _track_key(meta: Any) -> Optional[Tuple[str, str, int]]:
    """构造曲目身份键：标题 + 首位艺人 + 时长；缺标题时不参与同曲判定。"""
    title = _normalize(getattr(meta, "title", ""))
    if not title:
        return None
    artists = [str(item).strip() for item in (getattr(meta, "artists", None) or []) if str(item).strip()]
    artist = _normalize(artists[0]) if artists else ""
    return title, artist, _duration(meta) or -1


def _duration_close(left: int, right: int) -> bool:
    """判断两个时长是否落在容差范围内。"""
    if left < 0 or right < 0:
        return True
    return abs(left - right) <= _DURATION_TOLERANCE


def _file_entry(path: Path, meta: Any) -> Dict[str, Any]:
    """构造重复清单中的单个文件信息。"""
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    return {
        "path": str(path),
        "name": path.name,
        "dir": str(path.parent),
        "ext": path.suffix.lower(),
        "size": size,
        "lossless": _lossless_flag(meta),
        "bitrate": _bitrate(meta),
    }


def _rank(entry: Dict[str, Any]) -> Tuple[bool, int, int, int]:
    """排序权重：无损优先、码率高优先、体积大优先、路径短优先。"""
    return (
        bool(entry.get("lossless")),
        int(entry.get("bitrate") or 0),
        int(entry.get("size") or 0),
        -len(str(entry.get("path") or "")),
    )


def _group(kind: str, entries: List[Dict[str, Any]], key: str, album: str = "") -> Optional[Dict[str, Any]]:
    """把同一组文件整理为清单条目，保留信息最完整的一份。"""
    if len(entries) < 2:
        return None
    ordered = sorted(entries, key=_rank, reverse=True)
    keep = ordered[0]
    others = ordered[1:]
    wasted = sum(int(item.get("size") or 0) for item in others)
    return {
        "id": f"{kind}:{key}",
        "kind": kind,
        "title": Path(str(keep.get("name"))).stem,
        "album": album,
        "keep": keep["path"],
        "files": ordered,
        "duplicates": [item["path"] for item in others],
        "wasted": wasted,
    }


def find_duplicates(
    paths: Iterable[Path],
    read_meta: Callable[[Path], Any],
    modes: Iterable[str] = DUPLICATE_MODES,
    limit: int = 20000,
) -> Dict[str, Any]:
    """扫描音频路径，返回完全重复与同曲多版本分组。

    :param paths: 待检测的音频路径
    :param read_meta: 读取元数据的回调，返回含 title/artists/duration 的对象
    :param modes: 检测方式，exact 表示文件内容完全一致，same_track 表示同一曲目的不同版本
    :param limit: 单次最多处理的文件数
    :return: 分组清单与其统计信息
    """
    selected = [str(item) for item in (modes or []) if str(item) in DUPLICATE_MODES]
    selected = selected or list(DUPLICATE_MODES)
    files = sorted(Path(item) for item in paths)[: max(1, int(limit))]
    metas: Dict[str, Any] = {}
    groups: List[Dict[str, Any]] = []
    content_keys: Dict[str, str] = {}
    exact_duplicates: set[str] = set()

    def meta_for(path: Path) -> Any:
        """按路径缓存元数据读取结果。"""
        key = str(path)
        if key not in metas:
            try:
                metas[key] = read_meta(path)
            except Exception:  # noqa: BLE001
                metas[key] = None
        return metas[key]

    if "exact" in selected:
        by_size: Dict[int, List[Path]] = {}
        for path in files:
            try:
                size = path.stat().st_size
            except OSError:
                continue
            by_size.setdefault(size, []).append(path)
        for size, bucket in by_size.items():
            if len(bucket) < 2:
                continue
            by_hash: Dict[str, List[Dict[str, Any]]] = {}
            for path in bucket:
                digest = _quick_hash(path, size)
                if not digest:
                    continue
                content_keys[str(path)] = f"{size}:{digest}"
                by_hash.setdefault(digest, []).append(_file_entry(path, meta_for(path)))
            for digest, entries in by_hash.items():
                group = _group("exact", entries, digest)
                if group is None:
                    continue
                groups.append(group)
                exact_duplicates.update(group["duplicates"])

    if "same_track" in selected:
        by_track: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        for path in files:
            meta = meta_for(path)
            if meta is None:
                continue
            key = _track_key(meta)
            if not key:
                continue
            by_track.setdefault(key[:2], []).append(_file_entry(path, meta) | {"_duration": key[2]})
        for (title, artist), entries in by_track.items():
            if len(entries) < 2:
                continue
            # 时长接近的文件归为一组，避免同名不同曲被误判
            pending = sorted(entries, key=lambda item: int(item.get("_duration") or -1))
            clusters: List[List[Dict[str, Any]]] = []
            for item in pending:
                duration = int(item.get("_duration") or -1)
                for cluster in clusters:
                    if _duration_close(int(cluster[0].get("_duration") or -1), duration):
                        cluster.append(item)
                        break
                else:
                    clusters.append([item])
            for cluster in clusters:
                if len(cluster) < 2:
                    continue
                # 完全相同的副本已在上一步报告，这里只保留每份内容的一个代表
                filtered: List[Dict[str, Any]] = []
                seen_content: set[str] = set()
                for item in cluster:
                    # 完全重复组已经报告过的副本，不再在同曲清单里重复出现
                    if item["path"] in exact_duplicates:
                        continue
                    key = content_keys.get(item["path"])
                    if key is not None:
                        if key in seen_content:
                            continue
                        seen_content.add(key)
                    filtered.append(item)
                cluster = filtered
                if len(cluster) < 2:
                    continue
                album = str(getattr(meta_for(Path(cluster[0]["path"])), "album", "") or "")
                group = _group("same_track", cluster, f"{title}|{artist}", album)
                if group is not None:
                    groups.append(group)

    groups.sort(key=lambda item: int(item.get("wasted") or 0), reverse=True)
    duplicates = sum(len(item.get("duplicates") or []) for item in groups)
    return {
        "groups": groups,
        "stats": {
            "scanned": len(files),
            "modes": selected,
            "groups": len(groups),
            "exact_groups": sum(1 for item in groups if item["kind"] == "exact"),
            "track_groups": sum(1 for item in groups if item["kind"] == "same_track"),
            "duplicate_files": duplicates,
            "wasted_bytes": sum(int(item.get("wasted") or 0) for item in groups),
        },
    }
