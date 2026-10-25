"""音乐标签刮削插件：按 music-tag 思路多源补全本地音乐标签、歌词与封面。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.schemas.types import MessageType
from app.sdk.logging import logger
from app.sdk.plugin import _PluginBase

from .api import build_api_routes
from .engine import DEFAULT_CONFIG, MusicTagEngine, normalize_config


class MusicTagScraper(_PluginBase):
    """音乐标签刮削插件主类。"""

    plugin_name = "音乐标签刮削"
    plugin_desc = (
        "按目录扫描本地音乐，使用豆瓣音乐 / MusicBrainz / TheAudioDB 多源补全标题、艺人、专辑、年份、"
        "曲序与流派，并通过 LRCLIB / AMLL 写入同名歌词（可带 LRC 头部信息），同时补齐内嵌封面与"
        "专辑目录 cover.jpg/folder.jpg；试跑结果可勾选执行，失败条目可单条重试，首页提供处理仪表板；"
        "默认只补空缺，不重命名、不移动、不删除文件。"
    )
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main/icons/163music_A.png"
    plugin_version = "1.2.0"
    plugin_label = "音乐,标签,歌词"
    plugin_author = "miguelito39721"
    plugin_config_prefix = "musictagscraper_"
    plugin_order = 70
    auth_level = 1

    _enabled = False
    _config: Dict[str, Any] = dict(DEFAULT_CONFIG)
    _engine: Optional[MusicTagEngine] = None

    def init_plugin(self, config: dict = None) -> None:
        """根据插件配置初始化运行状态与引擎。"""
        self.stop_service()
        self._config = normalize_config(config)
        self._enabled = bool(self._config.get("enabled"))
        try:
            self._engine = MusicTagEngine(
                config=self._config,
                data_dir=self.get_data_path(),
                notify=self._send_notify,
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"音乐标签刮削：引擎初始化失败：{err}")
            self._engine = None
        if self._enabled:
            logger.info("音乐标签刮削插件已启用")

    def get_state(self) -> bool:
        """返回插件启用状态。"""
        return bool(self._enabled)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """返回远程命令列表（本插件不提供命令）。"""
        return []

    @staticmethod
    def get_render_mode() -> Tuple[str, str]:
        """声明插件使用 Vue 联邦组件渲染界面。"""
        return "vue", "dist/assets"

    def get_api(self) -> List[Dict[str, Any]]:
        """返回插件 API 路由。"""
        return build_api_routes(self)

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """Vue 联邦模式下返回默认配置模型。"""
        return [], dict(self._config or DEFAULT_CONFIG)

    def get_page(self) -> List[dict]:
        """Vue 联邦模式下详情页由远程 Page 组件渲染。"""
        return []

    def get_sidebar_nav(self) -> List[Dict[str, Any]]:
        """声明主界面侧栏入口（可在配置中关闭）。"""
        if not self.get_state() or not self._config.get("show_sidebar_nav"):
            return []
        return [
            {
                "nav_key": "main",
                "title": "音乐标签刮削",
                "icon": "mdi-music-note-plus",
                "section": "organize",
                "permission": "manage",
                "order": 70,
            }
        ]

    def get_service(self) -> List[Dict[str, Any]]:
        """注册定时补全服务。"""
        if not self.get_state():
            return []
        hours = int(self._config.get("schedule_hours") or 0)
        if hours <= 0:
            return []
        return [
            {
                "id": f"{self.__class__.__name__}Scan",
                "name": "音乐标签定时补全",
                "trigger": "interval",
                "func": self._scheduled_scan,
                "kwargs": {"hours": max(1, hours)},
            }
        ]

    def stop_service(self) -> None:
        """停止后台任务并释放资源。"""
        if self._engine is not None:
            self._engine.stop()

    def _scheduled_scan(self) -> None:
        """定时补全入口。"""
        if self._engine is None:
            return
        result = self._engine.start_run({})
        if not result.get("started"):
            logger.info(f"音乐标签刮削：定时任务未启动：{result.get('message')}")

    def _send_notify(self, title: str, text: str) -> None:
        """发送插件通知。"""
        try:
            self.post_message(mtype=MessageType.Plugin, title=title, text=text)
        except Exception as err:  # noqa: BLE001
            logger.warning(f"音乐标签刮削：通知发送失败：{err}")

    # ------------------------------------------------------------------ API

    def engine_status(self) -> Dict[str, Any]:
        """返回引擎状态。"""
        if self._engine is None:
            return {"enabled": False, "running": False, "message": "引擎未初始化"}
        data = self._engine.status()
        data["daily"] = self._engine.daily_stats()
        return data

    def engine_config(self) -> Dict[str, Any]:
        """返回当前生效配置。"""
        return dict(self._config or DEFAULT_CONFIG)

    def engine_preview(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """试跑：扫描并预览，不写文件。"""
        if self._engine is None:
            return {"success": False, "message": "引擎未初始化"}
        try:
            return {"success": True, **self._engine.preview(payload or {})}
        except Exception as err:  # noqa: BLE001
            logger.error(f"音乐标签刮削：试跑失败：{err}")
            return {"success": False, "message": str(err)}

    def engine_run(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """启动补全任务。"""
        if self._engine is None:
            return {"started": False, "message": "引擎未初始化"}
        try:
            return self._engine.start_run(payload or {})
        except Exception as err:  # noqa: BLE001
            logger.error(f"音乐标签刮削：启动失败：{err}")
            return {"started": False, "message": str(err)}

    def engine_stop(self) -> Dict[str, Any]:
        """停止当前任务。"""
        if self._engine is None:
            return {"stopping": False, "message": "引擎未初始化"}
        return self._engine.cancel()

    def engine_retry(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """重试失败条目，可只重试 payload 中指定的文件。"""
        if self._engine is None:
            return {"started": False, "message": "引擎未初始化"}
        data = payload or {}
        keys = [str(item) for item in (data.get("keys") or []) if str(item or "").strip()]
        return self._engine.retry_failures(keys or None)

    def engine_clear(self) -> Dict[str, Any]:
        """清空处理记录与失败清单。"""
        if self._engine is None:
            return {"cleared": 0, "message": "引擎未初始化"}
        return self._engine.clear_records()

    # -------------------------------------------------------------- 仪表板

    def get_dashboard_meta(self) -> Optional[List[Dict[str, str]]]:
        """返回首页仪表板元信息。"""
        if not self.get_state() or not self._config.get("dashboard"):
            return []
        return [{"key": "musictagscraper", "name": "音乐标签刮削"}]

    def get_dashboard(
        self, key: str, **kwargs: Any
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], Optional[List[Dict[str, Any]]]]]:
        """返回首页仪表板配置与今日处理数据。"""
        if not self.get_state() or not self._config.get("dashboard") or self._engine is None:
            return None
        data = self._engine.dashboard_stats()
        today = data.get("today") or {}
        last_run = data.get("last_run") or {}
        run = data.get("run") or {}
        attrs = {"refresh": 120, "title": "音乐标签刮削"}
        cols = {"cols": 12, "md": 6}
        content: List[Dict[str, Any]] = [
            {
                "component": "VRow",
                "content": [
                    self._dash_card("今日更新", str(today.get("updated", 0)), "mdi-music-note", 6, 3),
                    self._dash_card("今日歌词", str(today.get("lyrics", 0)), "mdi-text-box-outline", 6, 3),
                    self._dash_card("今日目录封面", str(today.get("folder_cover", 0)), "mdi-image-outline", 6, 3),
                    self._dash_card("失败条目", str(data.get("failure_count", 0)), "mdi-alert-circle-outline", 6, 3),
                ],
            }
        ]
        if data.get("running"):
            total = int(run.get("total") or 0)
            finished = int(run.get("finished") or 0)
            percent = round(finished * 100 / total) if total else 0
            content.append(
                {
                    "component": "VAlert",
                    "props": {
                        "type": "info",
                        "variant": "tonal",
                        "density": "compact",
                        "title": f"正在处理 {percent}%",
                        "text": str(run.get("message") or ""),
                    },
                }
            )
        elif last_run.get("state"):
            state_text = {
                "finished": "上次完成",
                "cancelled": "上次已停止",
                "failed": "上次失败",
            }.get(str(last_run.get("state")), str(last_run.get("state")))
            content.append(
                {
                    "component": "div",
                    "props": {"class": "text-caption text-medium-emphasis mt-2"},
                    "text": (
                        f"{state_text} ｜ 更新 {last_run.get('updated', 0)} ｜ "
                        f"跳过 {last_run.get('skipped', 0)} ｜ 失败 {last_run.get('failed', 0)} ｜ "
                        f"{last_run.get('finished_at') or ''}"
                    ),
                }
            )
        content.append(
            {
                "component": "div",
                "props": {"class": "text-caption text-medium-emphasis mt-1"},
                "text": f"累计处理音频 {data.get('processed_total', 0)} 个",
            }
        )
        return cols, attrs, content

    @staticmethod
    def _dash_card(title: str, value: str, icon: str, cols: int, md: int) -> Dict[str, Any]:
        """构造仪表板统计卡片。"""
        return {
            "component": "VCol",
            "props": {"cols": cols, "md": md},
            "content": [
                {
                    "component": "VCard",
                    "props": {"variant": "tonal"},
                    "content": [
                        {
                            "component": "VCardText",
                            "props": {"class": "d-flex align-center"},
                            "content": [
                                {
                                    "component": "VIcon",
                                    "props": {"icon": icon, "size": 30, "class": "me-3", "color": "primary"},
                                },
                                {
                                    "component": "div",
                                    "content": [
                                        {
                                            "component": "div",
                                            "props": {"class": "text-caption text-medium-emphasis"},
                                            "text": title,
                                        },
                                        {
                                            "component": "div",
                                            "props": {"class": "text-h6 font-weight-bold"},
                                            "text": value,
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                }
            ],
        }
