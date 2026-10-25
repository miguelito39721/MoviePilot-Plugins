"""音乐标签刮削引擎：扫描本地音乐目录，多源补全标签、歌词与封面。

引擎只读写音频文件的标签与同名旁挂歌词，不重命名、不移动、不删除文件。
"""

from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mutagen import File as MutagenFile
from mutagen.apev2 import APEv2
from mutagen.flac import FLAC
from mutagen.mp4 import MP4

from app.application.audio import AudioMetadataHelper
from app.chain.douban import DoubanChain
from app.chain.lyrics import LyricsChain
from app.chain.musicbrainz import MusicBrainzChain
from app.chain.theaudiodb import TheAudioDbChain
from app.domain.context import MusicInfo, MusicLyrics
from app.domain.meta.metamusic import MetaMusic
from app.sdk.logging import logger
from app.sdk.network import RequestUtils

from .dedupe import DUPLICATE_MODES, find_duplicates

# 支持的音频后缀
AUDIO_EXTENSIONS = {
    ".flac", ".wav", ".mp3", ".m4a", ".aac", ".ape", ".aiff", ".aif",
    ".ogg", ".opus", ".wma", ".dsf", ".dff", ".wv",
}
# 需要扫描时忽略的目录名
_IGNORED_DIRS = {"@eadir", "#recycle", "lost+found", ".git", "__pycache__"}
# 歌词文件后缀（与宿主保持一致，仅用于判定已有歌词）
LYRICS_EXTENSIONS = (".lrc", ".txt", ".lyricsfile.yaml")
# 单次运行内的外部查询缓存上限
_CACHE_LIMIT = 2000
# 状态文件版本
_STATE_VERSION = 1
# 专辑目录封面的候选文件名，用于判断是否需要补写
FOLDER_COVER_CANDIDATES = (
    "cover.jpg", "cover.png", "folder.jpg", "folder.png",
    "front.jpg", "front.png", "album.jpg", "album.png",
)
# 允许写入的目录封面文件名
FOLDER_COVER_CHOICES = ("cover.jpg", "folder.jpg")
# 歌词头部元信息标记
_LRC_META_PATTERN = re.compile(r"^\s*\[(ti|ar|al|by|offset|re|ve):", re.IGNORECASE)

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "music_dirs": ["/vol2/1000/music"],
    "exclude_dirs": [],
    "sources": ["douban", "musicbrainz", "theaudiodb"],
    "fill_tags": True,
    "write_cover": True,
    "write_folder_cover": True,
    "folder_cover_names": ["cover.jpg"],
    "write_lyrics": True,
    "lrc_metadata": True,
    "overwrite": False,
    "overwrite_lyrics": False,
    "min_score": 0.62,
    "concurrency": 2,
    "max_files_per_run": 200,
    "schedule_hours": 0,
    "notify": True,
    "show_sidebar_nav": True,
    "dashboard": True,
    "dedupe_modes": ["exact", "same_track"],
    "quarantine_dir": "",
}

# 来源名称到处理链的映射
_SOURCE_LABELS = {
    "douban": "豆瓣音乐",
    "musicbrainz": "MusicBrainz",
    "theaudiodb": "TheAudioDB",
}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    """把配置值收敛到指定整数区间。"""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    """把配置值收敛到指定浮点区间。"""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _as_str_list(value: Any) -> List[str]:
    """把配置值整理为去空的字符串列表。"""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.splitlines() if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item or "").strip()]
    return []


def normalize_config(config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """合并默认配置并做类型与区间收敛。"""
    data = dict(DEFAULT_CONFIG)
    if isinstance(config, dict):
        data.update({key: value for key, value in config.items() if key in DEFAULT_CONFIG})
    data["enabled"] = bool(data.get("enabled"))
    dirs = _as_str_list(data.get("music_dirs")) or list(DEFAULT_CONFIG["music_dirs"])
    data["music_dirs"] = dirs
    data["exclude_dirs"] = _as_str_list(data.get("exclude_dirs"))
    sources = [item for item in _as_str_list(data.get("sources")) if item in _SOURCE_LABELS]
    data["sources"] = sources or list(DEFAULT_CONFIG["sources"])
    for key in (
        "fill_tags", "write_cover", "write_folder_cover", "write_lyrics",
        "lrc_metadata", "overwrite", "overwrite_lyrics", "notify",
        "show_sidebar_nav", "dashboard",
    ):
        data[key] = bool(data.get(key))
    cover_names = [
        item for item in _as_str_list(data.get("folder_cover_names"))
        if item.lower() in FOLDER_COVER_CHOICES
    ]
    data["folder_cover_names"] = list(dict.fromkeys(cover_names)) or list(DEFAULT_CONFIG["folder_cover_names"])
    dedupe_modes = [item for item in _as_str_list(data.get("dedupe_modes")) if item in DUPLICATE_MODES]
    data["dedupe_modes"] = list(dict.fromkeys(dedupe_modes)) or list(DEFAULT_CONFIG["dedupe_modes"])
    data["quarantine_dir"] = str(data.get("quarantine_dir") or "").strip()
    data["min_score"] = _bounded_float(data.get("min_score"), 0.62, 0.3, 1.0)
    data["concurrency"] = _bounded_int(data.get("concurrency"), 2, 1, 8)
    data["max_files_per_run"] = _bounded_int(data.get("max_files_per_run"), 200, 1, 2000)
    data["schedule_hours"] = _bounded_int(data.get("schedule_hours"), 0, 0, 168)
    return data


def _normalize_text(value: Any) -> str:
    """归一化标题用于相似度比较：去括号内容、标点与大小写差异。"""
    text = str(value or "").strip().casefold()
    text = re.sub(r"[\(（\[【].*?[\)）\]】]", "", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    return text


def _similarity(left: Any, right: Any) -> float:
    """返回两段标题的相似度；空值返回 0。"""
    first, second = _normalize_text(left), _normalize_text(right)
    if not first or not second:
        return 0.0
    if first == second:
        return 1.0
    if first in second or second in first:
        return 0.9
    return difflib.SequenceMatcher(None, first, second).ratio()


def _now_text() -> str:
    """返回便于展示的当前时间文本。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _album_from_folder(folder: str, artist: str = "") -> str:
    """从目录名推断专辑名，去掉艺人前缀、年份与格式标记。"""
    text = re.sub(r"[\[\(（【].*?[\]\)）】]", " ", folder or "")
    text = text.replace("_", " ").strip()
    if artist and text.startswith(artist):
        text = text[len(artist):]
    text = text.lstrip(" -–—_")
    text = re.sub(r"\b(19|20)\d{2}\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—_")
    return text or (folder or "")


def _artist_from_folder(folder: str) -> str:
    """从「艺人 - 专辑」形式的目录名中推断艺人。"""
    text = str(folder or "").strip()
    for sep in (" - ", " – ", "_"):
        if sep in text:
            candidate = text.split(sep)[0].strip()
            if candidate and len(candidate) <= 40:
                return candidate
    return ""


def _clean_track_title(name: str) -> str:
    """清理文件名中的曲序号与方括号标记，得到可用的曲名。"""
    text = str(name or "").strip()
    text = re.sub(r"^[\(\[]?\d+[\)\]]?\s*", "", text)
    text = re.sub(r"[\[\(（【][^\]\)）】]*[\]\)）】]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -–—_")
    return text


def _image_suffix(data: bytes) -> Tuple[str, str]:
    """按图片文件头判断 MIME 与扩展名，未知格式按 JPEG 处理。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", ".png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", ".webp"
    if data[:3] == b"GIF":
        return "image/gif", ".gif"
    return "image/jpeg", ".jpg"


def _embedded_cover(path: Path) -> Optional[Tuple[bytes, str]]:
    """从音频内嵌封面中取出第一张图片，返回图片字节与 MIME。"""
    try:
        audio = MutagenFile(path)
    except Exception as err:  # noqa: BLE001
        logger.debug(f"音乐标签刮削：读取内嵌封面失败 {path} - {err}")
        return None
    if audio is None:
        return None
    if isinstance(audio, FLAC) and audio.pictures:
        picture = audio.pictures[0]
        if picture.data:
            return picture.data, picture.mime or "image/jpeg"
    tags = getattr(audio, "tags", None)
    if tags is None:
        return None
    if isinstance(audio, MP4):
        covers = tags.get("covr")
        if covers:
            item = covers[0]
            fmt = getattr(item, "imageformat", None)
            data = bytes(item)
            return data, "image/png" if fmt == 14 else "image/jpeg"
    getall = getattr(tags, "getall", None)
    if callable(getall):
        pictures = getall("APIC")
        if pictures:
            return pictures[0].data, pictures[0].mime or "image/jpeg"
        asf_pictures = getall("WM/Picture")
        if asf_pictures:
            raw = bytes(asf_pictures[0].value or b"")
            offset = raw.find(b"\xff\xd8\xff")
            if offset < 0:
                offset = raw.find(b"\x89PNG\r\n\x1a\n")
            if offset >= 0:
                return raw[offset:], _image_suffix(raw[offset:])[0]
    if isinstance(tags, APEv2):
        for key in ("Cover Art (Front)", "Cover Art (Back)"):
            value = tags.get(key)
            if value is None:
                continue
            raw = bytes(getattr(value, "value", value) or b"")
            index = raw.find(b"\x00")
            data = raw[index + 1:] if 0 < index < 256 else raw
            if data:
                return data, _image_suffix(data)[0]
    return None


def _lrc_has_meta(content: str) -> bool:
    """判断歌词文本开头是否已有 LRC 元信息行。"""
    for line in str(content or "").splitlines()[:12]:
        if _LRC_META_PATTERN.match(line):
            return True
    return False


class MusicTagEngine:
    """音乐标签刮削引擎：扫描、多源匹配、写标签/歌词/封面。"""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        data_dir: Optional[Path] = None,
        notify: Optional[Any] = None,
    ) -> None:
        """初始化配置、状态存储与依赖。"""
        self._config = normalize_config(config)
        self._data_dir = Path(data_dir) if data_dir else Path("/config/temp/MusicTagScraper")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._data_dir / "state.json"
        self._notify = notify
        self._lock = threading.RLock()
        self._io_lock = threading.Lock()
        self._cover_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._run: Optional[Dict[str, Any]] = None
        self._state = self._load_state()
        # 单轮缓存：专辑查询与歌词查询避免重复请求
        self._album_cache: Dict[str, Dict[str, Any]] = {}
        self._lyrics_cache: Dict[str, Optional[MusicLyrics]] = {}
        self._cover_cache: Dict[str, Optional[bytes]] = {}
        # 单轮内已完成目录封面的目录集合，避免并发重复写同一专辑
        self._cover_dirs_done: set[str] = set()
        # 查重为后台任务：结果与进度单独保存，避免大库扫描阻塞页面请求
        self._dedupe_lock = threading.Lock()
        self._dedupe_thread: Optional[threading.Thread] = None
        self._dedupe_run: Dict[str, Any] = {}
        self._dedupe_result: Dict[str, Any] = {}

    # ------------------------------------------------------------------ 状态

    def _load_state(self) -> Dict[str, Any]:
        """读取本地状态文件。"""
        default: Dict[str, Any] = {
            "version": _STATE_VERSION,
            "records": {},
            "failures": {},
            "cover_dirs": {},
            "quarantine": {},
            "logs": [],
            "last_run": None,
            "stats": {},
        }
        try:
            if self._state_file.exists():
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    default.update(data)
        except Exception as err:  # noqa: BLE001
            logger.warning(f"音乐标签刮削：状态文件读取失败：{err}")
        for key in ("records", "failures", "cover_dirs", "quarantine"):
            if not isinstance(default.get(key), dict):
                default[key] = {}
        if not isinstance(default.get("logs"), list):
            default["logs"] = []
        return default

    def _save_state(self) -> None:
        """把状态写入磁盘（原子替换）。"""
        with self._lock:
            self._state["logs"] = list(self._state.get("logs") or [])[-300:]
            failures = self._state.get("failures")
            if isinstance(failures, dict) and len(failures) > 800:
                self._state["failures"] = dict(list(failures.items())[-800:])
            cover_dirs = self._state.get("cover_dirs")
            if isinstance(cover_dirs, dict) and len(cover_dirs) > 3000:
                self._state["cover_dirs"] = dict(list(cover_dirs.items())[-3000:])
            quarantine = self._state.get("quarantine")
            if isinstance(quarantine, dict) and len(quarantine) > 5000:
                self._state["quarantine"] = dict(list(quarantine.items())[-5000:])
            payload = dict(self._state)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        tmp = self._state_file.with_name(f"{self._state_file.name}.{os.getpid()}.tmp")
        try:
            with self._io_lock:
                tmp.write_text(text, encoding="utf-8")
                os.replace(tmp, self._state_file)
        except Exception as err:  # noqa: BLE001
            logger.warning(f"音乐标签刮削：状态写入失败：{err}")

    def _log(self, message: str, level: str = "info") -> None:
        """追加一条运行日志。"""
        entry = {"time": _now_text(), "level": level, "message": str(message)}
        with self._lock:
            self._state.setdefault("logs", []).append(entry)
        logger.info(f"音乐标签刮削：{message}") if level == "info" else logger.warning(
            f"音乐标签刮削：{message}"
        )

    def config(self) -> Dict[str, Any]:
        """返回当前生效配置。"""
        return dict(self._config)

    def status(self) -> Dict[str, Any]:
        """返回运行状态、统计与最近日志。"""
        with self._lock:
            records = dict(self._state.get("records") or {})
            failures = dict(self._state.get("failures") or {})
            cover_dirs = dict(self._state.get("cover_dirs") or {})
            quarantine = dict(self._state.get("quarantine") or {})
            dedupe = dict(self._state.get("dedupe") or {})
            logs = list(self._state.get("logs") or [])[-40:]
            stats = dict(self._state.get("stats") or {})
            last_run = self._state.get("last_run")
        run = dict(self._run or {})
        failure_rows = sorted(
            [dict(entry) for entry in failures.values() if isinstance(entry, dict)],
            key=lambda item: str(item.get("time") or ""),
            reverse=True,
        )[:30]
        return {
            "enabled": self._config.get("enabled"),
            "running": bool(run.get("state") == "running"),
            "run": run,
            "last_run": last_run,
            "stats": stats,
            "processed_total": len(records),
            "failure_count": len(failures),
            "cover_dir_count": len(cover_dirs),
            "quarantined_count": len(quarantine),
            "quarantined_bytes": sum(
                int((item or {}).get("size") or 0)
                for item in quarantine.values() if isinstance(item, dict)
            ),
            "dedupe": dedupe,
            "dedupe_running": bool(self._dedupe_thread is not None and self._dedupe_thread.is_alive()),
            "today": self._today_stats(records),
            "failures": failure_rows,
            "logs": logs,
            "config": self.config(),
        }

    @staticmethod
    def _today_stats(records: Dict[str, Any]) -> Dict[str, int]:
        """统计当天处理的音频、歌词与封面数量。"""
        today = datetime.now().strftime("%Y-%m-%d")
        result = {"updated": 0, "lyrics": 0, "cover": 0, "folder_cover": 0}
        for entry in records.values():
            if not isinstance(entry, dict) or not str(entry.get("date") or "").startswith(today):
                continue
            result["updated"] += 1
            result["lyrics"] += 1 if entry.get("lyrics") else 0
            result["cover"] += 1 if entry.get("cover") else 0
            result["folder_cover"] += 1 if entry.get("folder_cover") else 0
        return result

    def daily_stats(self) -> List[Dict[str, Any]]:
        """返回最近若干天的处理统计（按日期聚合）。"""
        buckets: Dict[str, Dict[str, int]] = {}
        with self._lock:
            records = dict(self._state.get("records") or {})
        for entry in records.values():
            if not isinstance(entry, dict):
                continue
            day = str(entry.get("date") or "")[:10]
            if not day:
                continue
            bucket = buckets.setdefault(
                day, {"updated": 0, "lyrics": 0, "cover": 0, "folder_cover": 0}
            )
            bucket["updated"] += 1
            bucket["lyrics"] += 1 if entry.get("lyrics") else 0
            bucket["cover"] += 1 if entry.get("cover") else 0
            bucket["folder_cover"] += 1 if entry.get("folder_cover") else 0
        return [
            {"date": day, **buckets[day]}
            for day in sorted(buckets)[-14:]
        ]

    # ------------------------------------------------------------------ 扫描

    def _iter_audio_files(self, dirs: List[str], excludes: List[str]) -> List[Path]:
        """遍历配置目录下的音频文件。"""
        excluded = [Path(item).expanduser() for item in excludes]
        # 隔离目录可能位于音乐库同级或内部，始终不参与扫描
        quarantine = self.quarantine_root()
        if quarantine is not None:
            excluded.append(quarantine)
        results: List[Path] = []
        for raw in dirs:
            root = Path(raw).expanduser()
            if not root.exists():
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                current = Path(dirpath)
                dirnames[:] = [
                    name for name in dirnames
                    if name not in _IGNORED_DIRS and not any(
                        str(current / name).startswith(str(item)) for item in excluded
                    )
                ]
                if any(str(current).startswith(str(item)) for item in excluded):
                    continue
                for name in filenames:
                    path = current / name
                    if path.suffix.lower() in AUDIO_EXTENSIONS and not name.startswith("."):
                        results.append(path)
        results.sort()
        return results

    def _lyrics_path(self, path: Path) -> Path:
        """返回音频对应的歌词路径。"""
        return path.with_name(f"{path.stem}.lrc")

    def _has_lyrics(self, path: Path) -> bool:
        """判断音频旁是否已有歌词文件。"""
        return any(path.with_name(f"{path.stem}{ext}").exists() for ext in LYRICS_EXTENSIONS)

    def _folder_cover_names(self) -> List[str]:
        """返回配置的专辑目录封面文件名。"""
        names = [
            str(item).strip() for item in (self._config.get("folder_cover_names") or [])
            if str(item).strip().lower() in FOLDER_COVER_CHOICES
        ]
        return names or list(DEFAULT_CONFIG["folder_cover_names"])

    def _existing_folder_cover(self, directory: Path) -> Optional[Path]:
        """返回目录中已存在的封面文件路径。"""
        for name in FOLDER_COVER_CANDIDATES:
            candidate = directory / name
            if candidate.is_file() and candidate.stat().st_size > 0:
                return candidate
        return None

    def _folder_cover_needed(self, directory: Path) -> bool:
        """判断是否仍需要为该目录补写封面文件。"""
        if not self._config.get("write_folder_cover"):
            return False
        if self._is_music_root(directory):
            return False
        if self._existing_folder_cover(directory) is not None:
            return False
        return True

    def _is_music_root(self, directory: Path) -> bool:
        """判断目录是否为配置的音乐根目录，避免把封面写到音乐库根上。"""
        roots = {
            str(Path(str(item)).expanduser()) for item in (self._config.get("music_dirs") or [])
        }
        return str(directory) in roots

    def _ensure_folder_cover(
        self,
        directory: Path,
        album: Dict[str, Any],
        audio_path: Path,
    ) -> Tuple[bool, str]:
        """为专辑目录写封面文件；优先在线封面，其次音频内嵌封面。"""
        if not self._config.get("write_folder_cover"):
            return False, "disabled"
        if not directory.is_dir():
            return False, "missing_dir"
        if self._is_music_root(directory):
            return False, "music_root"
        existing = self._existing_folder_cover(directory)
        if existing is not None and not self._config.get("overwrite"):
            return False, "exists"
        with self._cover_lock:
            if str(directory) in self._cover_dirs_done:
                return False, "exists"
            if self._existing_folder_cover(directory) is not None and not self._config.get("overwrite"):
                self._cover_dirs_done.add(str(directory))
                return False, "exists"
            data: Optional[bytes] = None
            mime = "image/jpeg"
            source = ""
            cover_url = str(album.get("cover_url") or "")
            if cover_url:
                data = self._fetch_cover(cover_url)
                if data:
                    mime = _image_suffix(data)[0]
                    source = "online"
            if not data:
                embedded = _embedded_cover(audio_path)
                if embedded:
                    data, mime = embedded
                    source = "embedded"
            if not data or len(data) < 128:
                self._cover_dirs_done.add(str(directory))
                return False, "no_cover"
            suffix = _image_suffix(data)[1]
            written: List[str] = []
            for name in self._folder_cover_names():
                target = directory / f"{Path(name).stem}{suffix}"
                if target.exists() and not self._config.get("overwrite"):
                    continue
                tmp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
                try:
                    tmp.write_bytes(data)
                    os.replace(tmp, target)
                    written.append(target.name)
                except Exception as err:  # noqa: BLE001
                    logger.warning(f"音乐标签刮削：目录封面写入失败 {target} - {err}")
                    try:
                        tmp.unlink(missing_ok=True)
                    except OSError:
                        pass
            self._cover_dirs_done.add(str(directory))
            if not written:
                return False, "exists"
            with self._lock:
                self._state.setdefault("cover_dirs", {})[str(directory)] = {
                    "time": _now_text(),
                    "files": written,
                    "source": source,
                    "mime": mime,
                }
            return True, source

    def _fingerprint(self, path: Path) -> str:
        """构造文件指纹，用于跳过未变更文件。"""
        try:
            stat = path.stat()
        except OSError:
            return ""
        return f"{stat.st_size}:{int(stat.st_mtime)}"

    def _build_job(self, path: Path) -> Optional[Dict[str, Any]]:
        """读取一个音频文件的标签并生成待处理任务描述。"""
        try:
            meta = AudioMetadataHelper.read(path)
        except Exception as err:  # noqa: BLE001
            logger.debug(f"音乐标签刮削：读取标签失败 {path} - {err}")
            return None
        if meta is None:
            meta = AudioMetadataHelper.read_filename(path)
        title = str(getattr(meta, "title", "") or "").strip()
        artists = [str(item).strip() for item in (getattr(meta, "artists", None) or []) if str(item).strip()]
        album = str(getattr(meta, "album", "") or "").strip()
        album_artist = str(getattr(meta, "album_artist", "") or "").strip()
        year = getattr(meta, "year", None)
        track = getattr(meta, "track_number", None)
        missing: List[str] = []
        if not title:
            missing.append("title")
        if not artists:
            missing.append("artist")
        if not album:
            missing.append("album")
        if not year:
            missing.append("year")
        if not track:
            missing.append("track")
        has_lyrics = self._has_lyrics(path)
        if not has_lyrics:
            missing.append("lyrics")
        folder_cover_ok = not self._folder_cover_needed(path.parent)
        return {
            "key": str(path),
            "path": str(path),
            "dir": str(path.parent),
            "name": path.name,
            "stem": path.stem,
            "ext": path.suffix.lower(),
            "fingerprint": self._fingerprint(path),
            "title": _clean_track_title(title or path.stem),
            "artists": artists,
            "album": album,
            "album_artist": album_artist or (artists[0] if artists else ""),
            "year": year,
            "track": track,
            "missing": missing,
            "has_lyrics": has_lyrics,
            "folder_cover_ok": folder_cover_ok,
            "folder": path.parent.name,
            "size": path.stat().st_size if path.exists() else 0,
        }

    def scan(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """扫描目录并返回任务清单与统计（不写文件）。"""
        payload = payload or {}
        dirs = _as_str_list(payload.get("music_dirs")) or list(self._config.get("music_dirs") or [])
        excludes = list(self._config.get("exclude_dirs") or [])
        limit = _bounded_int(
            payload.get("limit"),
            int(self._config.get("max_files_per_run") or 200),
            1,
            2000,
        )
        files = self._iter_audio_files(dirs, excludes)
        wanted = {
            str(Path(item).expanduser()) for item in _as_str_list(payload.get("paths"))
        }
        if wanted:
            files = [path for path in files if str(path) in wanted]
        jobs: List[Dict[str, Any]] = []
        skipped_processed = 0
        missing_cover_dirs: set[str] = set()
        with self._lock:
            records = dict(self._state.get("records") or {})
        for path in files:
            job = self._build_job(path)
            if job is None:
                continue
            if not job.get("folder_cover_ok"):
                missing_cover_dirs.add(job["dir"])
            if not job["missing"] and job.get("folder_cover_ok"):
                skipped_processed += 1
                continue
            record = records.get(str(path))
            if (
                isinstance(record, dict)
                and record.get("fingerprint") == job["fingerprint"]
                and not self._config.get("overwrite")
                and not payload.get("force")
                and (job.get("folder_cover_ok") or not self._config.get("write_folder_cover"))
            ):
                skipped_processed += 1
                continue
            jobs.append(job)
            if len(jobs) >= limit:
                break
        stats = {
            "scanned": len(files),
            "candidates": len(jobs),
            "skipped": skipped_processed,
            "missing_folder_cover": len(missing_cover_dirs),
            "dirs": dirs,
        }
        return {"jobs": jobs, "stats": stats}

    # ------------------------------------------------------------------ 匹配

    def _chain_for(self, source: str) -> Optional[Any]:
        """按来源名称返回对应的音乐元数据链实例。"""
        try:
            if source == "douban":
                return DoubanChain()
            if source == "musicbrainz":
                return MusicBrainzChain()
            if source == "theaudiodb":
                return TheAudioDbChain()
        except Exception as err:  # noqa: BLE001
            logger.warning(f"音乐标签刮削：来源 {source} 初始化失败：{err}")
        return None

    def _search(self, meta: MetaMusic, music_types: List[str], limit: int = 8) -> List[MusicInfo]:
        """按配置的来源顺序搜索音乐候选，失败时自动回退下一来源。"""
        results: List[MusicInfo] = []
        for source in self._config.get("sources") or []:
            chain = self._chain_for(str(source))
            if chain is None:
                continue
            try:
                candidates = chain.search_music(meta, limit=limit, music_types=music_types)
            except Exception as err:  # noqa: BLE001
                logger.debug(f"音乐标签刮削：{source} 搜索失败：{err}")
                continue
            for item in candidates or []:
                if isinstance(item, MusicInfo):
                    results.append(item)
            if results:
                break
        return results

    def _pick_candidate(
        self, candidates: List[MusicInfo], album_name: str, artist: str
    ) -> Optional[MusicInfo]:
        """按标题与艺人相似度挑选最佳候选。"""
        best: Optional[MusicInfo] = None
        best_score = 0.0
        threshold = float(self._config.get("min_score") or 0.62)
        for item in candidates:
            score = _similarity(item.title, album_name)
            if artist and _similarity(item.album_artist or (item.artists[0] if item.artists else ""), artist) >= 0.8:
                score += 0.15
            if item.year and album_name and str(item.year) in album_name:
                score += 0.05
            if score > best_score:
                best, best_score = item, score
        if best is None or best_score < threshold:
            return None
        return best

    def _album_metadata(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """按目录聚合查询专辑级元数据，命中结果按目录缓存。"""
        cache_key = job["dir"]
        if cache_key in self._album_cache:
            return self._album_cache[cache_key]
        artist = job.get("album_artist") or (
            job.get("artists")[0] if job.get("artists") else _artist_from_folder(job.get("folder") or "")
        )
        album_name = job.get("album") or _album_from_folder(job.get("folder") or "", artist)
        result: Dict[str, Any] = {}
        if album_name and _normalize_text(album_name):
            meta = MetaMusic(
                org_string=album_name,
                title=album_name,
                album=album_name,
                artists=[artist] if artist else [],
                album_artist=artist or None,
                year=job.get("year"),
            )
            candidates = self._search(meta, ["album"])
            picked = self._pick_candidate(candidates, album_name, artist)
            if picked is not None:
                result = {
                    "source": str(picked.media_source.value if hasattr(picked.media_source, "value") else picked.media_source or ""),
                    "title": picked.title,
                    "album": picked.album or picked.title,
                    "album_artist": picked.album_artist or (picked.artists[0] if picked.artists else artist),
                    "year": picked.year or picked.release_year,
                    "genres": list(picked.genres or []),
                    "total_tracks": picked.total_tracks,
                    "cover_url": picked.cover_url,
                    "musicbrainz_release_id": picked.musicbrainz_release_id,
                    "musicbrainz_release_group_id": picked.musicbrainz_release_group_id,
                    "media_id": picked.media_id,
                }
        self._album_cache[cache_key] = result
        return result

    def _fetch_cover(self, url: str) -> Optional[bytes]:
        """下载封面图片字节。"""
        if not url:
            return None
        if url in self._cover_cache:
            return self._cover_cache[url]
        data: Optional[bytes] = None
        try:
            response = RequestUtils().get_res(url, timeout=20)
            if response is not None and getattr(response, "status_code", 0) == 200:
                content = response.content
                if content and len(content) <= 8 * 1024 * 1024:
                    data = content
        except Exception as err:  # noqa: BLE001
            logger.debug(f"音乐标签刮削：封面下载失败 {url} - {err}")
        if len(self._cover_cache) < 500:
            self._cover_cache[url] = data
        return data

    def _lyrics_for(self, job: Dict[str, Any], album: Dict[str, Any]) -> Optional[MusicLyrics]:
        """查询歌词候选，命中结果按曲目缓存。"""
        if not self._config.get("write_lyrics"):
            return None
        title = job.get("title") or job.get("stem") or ""
        cache_key = f"{title}|{job.get('artists')}|{album.get('album') or job.get('album')}"
        if cache_key in self._lyrics_cache:
            return self._lyrics_cache[cache_key]
        artists = list(job.get("artists") or [])
        music = MusicInfo(
            music_type="recording",
            title=title,
            artists=artists,
            album=album.get("album") or job.get("album") or None,
            album_artist=album.get("album_artist") or job.get("album_artist") or None,
            year=album.get("year") or job.get("year"),
            track_number=job.get("track"),
        )
        lyrics: Optional[MusicLyrics] = None
        try:
            lyrics = LyricsChain().get_music_lyrics(music)
        except Exception as err:  # noqa: BLE001
            logger.debug(f"音乐标签刮削：歌词查询失败 {title} - {err}")
        if len(self._lyrics_cache) < _CACHE_LIMIT:
            self._lyrics_cache[cache_key] = lyrics
        return lyrics

    # ------------------------------------------------------------------ 写入

    @staticmethod
    def _lyrics_text(lyrics: MusicLyrics) -> Optional[Tuple[str, str]]:
        """把歌词候选转换为 (后缀, 内容)。"""
        synced = str(getattr(lyrics, "synced_lyrics", "") or "").strip()
        plain = str(getattr(lyrics, "plain_lyrics", "") or "").strip()
        if synced:
            return ".lrc", synced
        if plain:
            return ".lrc", plain
        return None

    def _write_lyrics(self, path: Path, lyrics: MusicLyrics) -> bool:
        """把歌词写入同名旁挂文件，遵守覆盖策略。"""
        converted = self._lyrics_text(lyrics)
        if not converted:
            return False
        extension, content = converted
        if self._config.get("lrc_metadata") and not _lrc_has_meta(content):
            header = self._lrc_header(path)
            if header:
                content = f"{header}{content}"
        target = path.with_name(f"{path.stem}{extension}")
        if target.exists() and not self._config.get("overwrite_lyrics") and not self._config.get("overwrite"):
            return False
        try:
            if target.exists():
                existing = target.read_text(encoding="utf-8", errors="ignore").strip()
                if existing == content.strip():
                    return False
            target.write_text(content if content.endswith("\n") else f"{content}\n", encoding="utf-8")
            return True
        except Exception as err:  # noqa: BLE001
            logger.warning(f"音乐标签刮削：歌词写入失败 {target} - {err}")
            return False

    @staticmethod
    def _lrc_header(path: Path) -> str:
        """构造 LRC 头部元信息，标题/艺人优先取标签，缺失时用文件名。"""
        try:
            meta = AudioMetadataHelper.read(path)
        except Exception:  # noqa: BLE001
            meta = None
        title = str(getattr(meta, "title", "") or "").strip() or _clean_track_title(path.stem)
        artists = [
            str(item).strip() for item in (getattr(meta, "artists", None) or []) if str(item).strip()
        ]
        album = str(getattr(meta, "album", "") or "").strip()
        lines = [f"[ti:{title}]"]
        if artists:
            lines.append(f"[ar:{' / '.join(artists)}]")
        if album:
            lines.append(f"[al:{album}]")
        lines.append("[by:MusicTagScraper]")
        return "".join(f"{line}\n" for line in lines)

    def _process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个音频：补标签、写歌词与封面。"""
        path = Path(job["path"])
        if not path.exists():
            return {"status": "skipped", "message": "文件不存在"}
        album = self._album_metadata(job) if self._config.get("fill_tags") else {}
        lyrics = self._lyrics_for(job, album)
        lyrics_written = False
        cover_written = False
        tags_written = False
        folder_cover_written = False
        folder_cover_state = "exists"

        if self._config.get("fill_tags") and album:
            artists = list(job.get("artists") or [])
            album_artist = album.get("album_artist") or job.get("album_artist") or ""
            if not artists and album_artist:
                artists = [album_artist]
            music = MusicInfo(
                music_type="recording",
                title=job.get("title") or job.get("stem"),
                artists=artists,
                album=album.get("album") or job.get("album") or None,
                album_artist=album_artist or None,
                year=album.get("year") or job.get("year"),
                track_number=job.get("track"),
                total_tracks=album.get("total_tracks"),
                genres=list(album.get("genres") or []),
                cover_url=album.get("cover_url"),
                musicbrainz_release_id=album.get("musicbrainz_release_id"),
                musicbrainz_release_group_id=album.get("musicbrainz_release_group_id"),
            )
            cover_data = None
            if self._config.get("write_cover") and album.get("cover_url"):
                cover_data = self._fetch_cover(str(album["cover_url"]))
            tags_written = AudioMetadataHelper.write(
                path=path,
                music=music,
                cover_data=cover_data,
                cover_mime="image/jpeg",
                overwrite=bool(self._config.get("overwrite")),
                write_tags=True,
                cover_overwrite=bool(self._config.get("overwrite")),
            )
            cover_written = bool(cover_data)

        if lyrics is not None:
            lyrics_written = self._write_lyrics(path, lyrics)

        if self._config.get("write_folder_cover"):
            folder_cover_written, folder_cover_state = self._ensure_folder_cover(
                path.parent, album, path
            )

        if not tags_written and not lyrics_written and not cover_written and not folder_cover_written:
            message = "未找到可补全的信息" if not album else "已是最新"
            if folder_cover_state == "no_cover":
                message = "缺少可用的封面图"
            return {"status": "skipped", "message": message, "album": album}

        with self._lock:
            self._state.setdefault("records", {})[job["key"]] = {
                "date": _now_text(),
                "fingerprint": job.get("fingerprint"),
                "album": album.get("album") or job.get("album"),
                "source": album.get("source") or "",
                "tags": bool(tags_written),
                "lyrics": bool(lyrics_written),
                "cover": bool(cover_written),
                "folder_cover": bool(folder_cover_written),
            }
        return {
            "status": "updated",
            "message": "已补全",
            "album": album,
            "tags": tags_written,
            "lyrics": lyrics_written,
            "cover": cover_written,
            "folder_cover": folder_cover_written,
            "folder_cover_state": folder_cover_state,
        }

    # ------------------------------------------------------------------ 运行

    def preview(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """试跑：扫描并按来源匹配，返回计划但不写文件。"""
        payload = payload or {}
        scan = self.scan(payload)
        jobs = scan["jobs"]
        sample = _bounded_int(payload.get("sample"), 0, 0, 20)
        items: List[Dict[str, Any]] = []
        for index, job in enumerate(jobs):
            album = self._album_metadata(job) if index < max(sample, 10) else {}
            items.append(
                {
                    "key": job["key"],
                    "name": job["name"],
                    "dir": job["dir"],
                    "folder": job.get("folder"),
                    "missing": job["missing"],
                    "album": album.get("album"),
                    "album_artist": album.get("album_artist"),
                    "year": album.get("year"),
                    "source": album.get("source"),
                    "cover": bool(album.get("cover_url")),
                    "folder_cover_ok": bool(job.get("folder_cover_ok")),
                }
            )
        return {"stats": scan["stats"], "items": items}

    def start_run(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """启动后台补全任务。"""
        payload = payload or {}
        with self._lock:
            if not self._config.get("enabled"):
                return {"started": False, "message": "插件未启用"}
            if self._thread is not None and self._thread.is_alive():
                return {"started": False, "message": "已有任务正在执行"}
            scan = self.scan(payload)
            jobs = scan["jobs"]
            if not jobs:
                return {"started": False, "message": "没有需要处理的音频", "stats": scan["stats"]}
            self._stop.clear()
            self._cover_dirs_done.clear()
            self._run = {
                "state": "running",
                "started_at": _now_text(),
                "total": len(jobs),
                "finished": 0,
                "updated": 0,
                "skipped": 0,
                "failed": 0,
                "folder_cover": 0,
                "message": f"待处理 {len(jobs)} 个音频",
                "stats": scan["stats"],
            }
            self._thread = threading.Thread(target=self._worker, args=(jobs,), daemon=True)
            self._thread.start()
        return {"started": True, "total": len(jobs), "stats": scan["stats"]}

    def cancel(self) -> Dict[str, Any]:
        """请求停止当前任务。"""
        self._stop.set()
        with self._lock:
            if self._run and self._run.get("state") == "running":
                self._run["message"] = "正在停止…"
        return {"stopping": True}

    def _worker(self, jobs: List[Dict[str, Any]]) -> None:
        """后台执行补全任务。"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        started = time.time()
        workers = max(1, int(self._config.get("concurrency") or 2))
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(self._process_job, job): job for job in jobs}
                for future in as_completed(futures):
                    job = futures[future]
                    if self._stop.is_set():
                        break
                    try:
                        result = future.result()
                    except Exception as err:  # noqa: BLE001
                        result = {"status": "failed", "message": str(err)}
                    with self._lock:
                        run = self._run or {}
                        run["finished"] = int(run.get("finished") or 0) + 1
                        status = result.get("status")
                        if status == "updated":
                            run["updated"] = int(run.get("updated") or 0) + 1
                            run["folder_cover"] = int(run.get("folder_cover") or 0) + (
                                1 if result.get("folder_cover") else 0
                            )
                        elif status == "failed":
                            run["failed"] = int(run.get("failed") or 0) + 1
                            self._state.setdefault("failures", {})[job["key"]] = {
                                "key": job["key"],
                                "name": job.get("name"),
                                "dir": job.get("dir"),
                                "message": result.get("message"),
                                "time": _now_text(),
                                "count": int((self._state.get("failures", {}).get(job["key"]) or {}).get("count") or 0) + 1,
                            }
                        else:
                            run["skipped"] = int(run.get("skipped") or 0) + 1
                        run["message"] = (
                            f"处理中 {run['finished']}/{run['total']}："
                            f"更新 {run['updated']}｜目录封面 {run.get('folder_cover', 0)}｜"
                            f"跳过 {run['skipped']}｜失败 {run['failed']}"
                        )
            summary = {
                "state": "cancelled" if self._stop.is_set() else "finished",
                "started_at": (self._run or {}).get("started_at"),
                "finished_at": _now_text(),
                "total": (self._run or {}).get("total", 0),
                "finished": (self._run or {}).get("finished", 0),
                "updated": (self._run or {}).get("updated", 0),
                "skipped": (self._run or {}).get("skipped", 0),
                "failed": (self._run or {}).get("failed", 0),
                "folder_cover": (self._run or {}).get("folder_cover", 0),
                "duration": round(time.time() - started, 1),
            }
            with self._lock:
                self._run = dict(self._run or {}, **summary)
                self._state["last_run"] = summary
                self._state["stats"] = {
                    "processed": len(self._state.get("records") or {}),
                    "failures": len(self._state.get("failures") or {}),
                    "time": _now_text(),
                }
            self._save_state()
            self._log(
                f"任务完成：更新 {summary['updated']}，跳过 {summary['skipped']}，"
                f"失败 {summary['failed']}，目录封面 {summary.get('folder_cover', 0)}，"
                f"用时 {summary['duration']}s"
            )
            self._notify_summary(summary)
        except Exception as err:  # noqa: BLE001
            logger.error(f"音乐标签刮削：任务异常 {err}", exc_info=True)
            self._log(f"任务异常：{err}", "error")
            with self._lock:
                self._run = dict(self._run or {}, state="failed", message=str(err))
            self._save_state()

    def _notify_summary(self, summary: Dict[str, Any]) -> None:
        """按配置发送批次完成通知。"""
        if not self._config.get("notify") or self._notify is None:
            return
        text = (
            f"共处理 {summary.get('total', 0)} 个音频：更新 {summary.get('updated', 0)}，"
            f"跳过 {summary.get('skipped', 0)}，失败 {summary.get('failed', 0)}，"
            f"目录封面 {summary.get('folder_cover', 0)}，用时 {summary.get('duration', 0)}s"
        )
        try:
            self._notify("音乐标签刮削", text)
        except Exception as err:  # noqa: BLE001
            logger.warning(f"音乐标签刮削：通知发送失败：{err}")

    def retry_failures(self, keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """重试失败清单中的文件，可只重试指定条目。"""
        picked = [str(item) for item in (keys or []) if str(item or "").strip()]
        with self._lock:
            failures = dict(self._state.get("failures") or {})
            targets = picked or list(failures)
            retry_keys = [key for key in targets if key in failures and Path(key).exists()]
            for key in targets:
                failures.pop(key, None)
            self._state["failures"] = failures
        if not retry_keys:
            self._save_state()
            return {"started": False, "message": "没有可重试的失败条目"}
        self._save_state()
        result = self.start_run({"paths": retry_keys, "limit": len(retry_keys), "force": True})
        result["retry"] = len(retry_keys)
        return result

    def clear_records(self) -> Dict[str, Any]:
        """清空处理记录与失败清单。"""
        with self._lock:
            count = len(self._state.get("records") or {})
            failed = len(self._state.get("failures") or {})
            self._state["records"] = {}
            self._state["failures"] = {}
            self._state["cover_dirs"] = {}
        self._save_state()
        return {"cleared": count, "failures": failed}

    # -------------------------------------------------------------- 重复检测

    def quarantine_root(self) -> Optional[Path]:
        """返回重复文件隔离目录：未配置时落在首个音乐目录同级，保证同一文件系统。"""
        configured = str(self._config.get("quarantine_dir") or "").strip()
        if configured:
            return Path(configured).expanduser()
        roots = [Path(item).expanduser() for item in (self._config.get("music_dirs") or [])]
        if not roots:
            return None
        return roots[0].parent / ".musictagscraper-duplicates"

    def _music_root_of(self, path: Path) -> Optional[Path]:
        """返回包含该文件且最贴近的音乐根目录。"""
        matched: Optional[Path] = None
        for item in self._config.get("music_dirs") or []:
            root = Path(item).expanduser()
            try:
                path.relative_to(root)
            except ValueError:
                continue
            if matched is None or len(str(root)) > len(str(matched)):
                matched = root
        return matched

    def detect_duplicates(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """扫描音乐目录并返回重复分组（只读，不移动任何文件）。"""
        payload = payload or {}
        dirs = _as_str_list(payload.get("music_dirs")) or list(self._config.get("music_dirs") or [])
        modes = [str(item) for item in _as_str_list(payload.get("modes")) if item in DUPLICATE_MODES]
        modes = modes or list(self._config.get("dedupe_modes") or [DUPLICATE_MODES[0]])
        limit = _bounded_int(payload.get("limit"), 5000, 1, 20000)
        files = self._iter_audio_files(dirs, list(self._config.get("exclude_dirs") or []))
        result = find_duplicates(files, AudioMetadataHelper.read, modes=modes, limit=limit)
        result["stats"]["dirs"] = dirs
        result["stats"]["quarantine_dir"] = str(self.quarantine_root() or "")
        with self._lock:
            self._state["dedupe"] = {
                "time": _now_text(),
                "stats": dict(result["stats"]),
            }
        self._save_state()
        return result

    def start_dedupe(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """在后台启动查重任务，避免大音乐库扫描阻塞页面。"""
        with self._dedupe_lock:
            if self._dedupe_thread is not None and self._dedupe_thread.is_alive():
                return {"started": False, "running": True, "message": "查重正在进行"}
            payload = dict(payload or {})
            self._dedupe_run = {
                "state": "running",
                "started_at": _now_text(),
                "message": "正在扫描音乐目录…",
            }

            def worker() -> None:
                """执行后台查重并保存结果。"""
                try:
                    result = self.detect_duplicates(payload)
                except Exception as err:  # noqa: BLE001
                    logger.error(f"音乐标签刮削：后台查重失败：{err}", exc_info=True)
                    with self._dedupe_lock:
                        self._dedupe_run = {"state": "failed", "message": str(err)}
                    return
                with self._dedupe_lock:
                    self._dedupe_result = result
                    self._dedupe_run = {
                        "state": "finished",
                        "started_at": self._dedupe_run.get("started_at"),
                        "finished_at": _now_text(),
                        "message": (
                            f"扫描 {result['stats'].get('scanned', 0)} 个音频，"
                            f"发现 {result['stats'].get('groups', 0)} 组重复"
                        ),
                    }

            self._dedupe_thread = threading.Thread(target=worker, daemon=True)
            self._dedupe_thread.start()
        return {"started": True, "running": True, "message": "查重已开始"}

    def dedupe_snapshot(self) -> Dict[str, Any]:
        """返回查重任务状态与最近一次结果。"""
        with self._dedupe_lock:
            thread = self._dedupe_thread
            running = bool(thread is not None and thread.is_alive())
            run = dict(self._dedupe_run)
            result = dict(self._dedupe_result)
        if running:
            run["state"] = "running"
        return {"running": running, "run": run, "result": result}

    def quarantine_files(self, paths: List[str]) -> Dict[str, Any]:
        """把选中的重复文件移入隔离目录，保留相对路径并记录可还原信息。"""
        root = self.quarantine_root()
        if root is None:
            return {"moved": 0, "failed": [], "message": "未配置音乐目录，无法确定隔离位置"}
        moved: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        for raw in paths or []:
            source = Path(str(raw or "")).expanduser()
            if not source.is_file():
                failed.append({"path": str(source), "reason": "文件不存在"})
                continue
            music_root = self._music_root_of(source)
            if music_root is None:
                failed.append({"path": str(source), "reason": "不在配置的音乐目录内"})
                continue
            try:
                relative = source.relative_to(music_root)
            except ValueError:
                failed.append({"path": str(source), "reason": "无法计算相对路径"})
                continue
            target = root / relative
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    stem, suffix = target.stem, target.suffix
                    index = 1
                    while target.exists():
                        target = target.with_name(f"{stem}.dup{index}{suffix}")
                        index += 1
                size = source.stat().st_size
                shutil.move(str(source), str(target))
            except Exception as err:  # noqa: BLE001
                logger.warning(f"音乐标签刮削：隔离重复文件失败 {source} - {err}")
                failed.append({"path": str(source), "reason": str(err)})
                continue
            with self._lock:
                self._state.setdefault("quarantine", {})[str(target)] = {
                    "origin": str(source),
                    "time": _now_text(),
                    "size": size,
                }
            moved.append({"origin": str(source), "target": str(target), "size": size})
        if moved:
            self._save_state()
            self._log(f"重复隔离：移动 {len(moved)} 个文件到 {root}")
        return {
            "moved": len(moved),
            "moved_bytes": sum(item["size"] for item in moved),
            "failed": failed,
            "quarantine_dir": str(root),
            "items": moved,
        }

    def restore_quarantine(self, paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """把隔离目录中的文件还原到原路径。"""
        picked = [str(item) for item in (paths or []) if str(item or "").strip()]
        with self._lock:
            records = dict(self._state.get("quarantine") or {})
            targets = picked or list(records)
        restored: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        for raw in targets:
            record = records.get(raw)
            if not isinstance(record, dict):
                failed.append({"path": raw, "reason": "没有隔离记录"})
                continue
            source = Path(raw)
            origin = Path(str(record.get("origin") or ""))
            if not source.is_file():
                failed.append({"path": raw, "reason": "隔离文件不存在"})
                continue
            if origin.exists():
                failed.append({"path": raw, "reason": "原位置已有同名文件"})
                continue
            try:
                origin.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(origin))
            except Exception as err:  # noqa: BLE001
                failed.append({"path": raw, "reason": str(err)})
                continue
            with self._lock:
                self._state.setdefault("quarantine", {}).pop(raw, None)
            restored.append({"origin": str(origin), "from": raw})
        if restored:
            self._save_state()
            self._log(f"重复还原：恢复 {len(restored)} 个文件")
        return {"restored": len(restored), "failed": failed, "items": restored}

    def dashboard_stats(self) -> Dict[str, Any]:
        """汇总首页仪表板需要的今日与最近批次数据。"""
        with self._lock:
            records = dict(self._state.get("records") or {})
            failures = dict(self._state.get("failures") or {})
            quarantine = dict(self._state.get("quarantine") or {})
            dedupe = dict(self._state.get("dedupe") or {})
            last_run = dict(self._state.get("last_run") or {})
        run = dict(self._run or {})
        return {
            "today": self._today_stats(records),
            "processed_total": len(records),
            "failure_count": len(failures),
            "quarantined_count": len(quarantine),
            "dedupe": dedupe.get("stats") if isinstance(dedupe.get("stats"), dict) else {},
            "last_run": last_run,
            "running": bool(run.get("state") == "running"),
            "run": run,
        }

    def stop(self) -> None:
        """停止后台任务。"""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3)
        self._thread = None
