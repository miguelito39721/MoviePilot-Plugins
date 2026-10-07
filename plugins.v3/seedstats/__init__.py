"""站点保种统计插件：按 tracker 汇总各站点做种情况，并合并站点账户信息。

统计在后台线程定时计算并缓存，页面与仪表板只读缓存，避免拖慢 Web 界面。
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.db.models.siteuserdata import SiteUserData
from app.db.site_oper import SiteOper
from app.plugins import _PluginBase
from app.sdk.logging import logger
from app.sdk.network import SitesHelper
from app.sdk.services import DownloaderHelper
from app.sdk.utilities import StringUtils

# 状态归类
_SEEDING_STATES = {"seeding", "seed_pending"}
_PAUSED_STATES = {"stopped", "paused"}
# 辅种任务标签
_CROSS_SEED_TAG = "辅种"
# 缓存键
_CACHE_KEY = "stats"
# 时魔估算允许的最大时间窗口（小时）
_MAX_HOURLY_WINDOW = 72


class SeedStats(_PluginBase):
    """站点保种统计插件。

    后台按配置周期读取下载器任务，按 tracker 归属统计各站点的做种数、
    辅种数等，并合并 MoviePilot 站点数据中的上传/下载/分享率/等级/魔力
    等信息；结果缓存后由插件详情页与首页仪表板展示。插件只读。
    """

    plugin_name = "站点保种统计"
    plugin_desc = "按 tracker 汇总各站点做种/辅种数量，并合并站点账户信息（上传/下载/分享率/等级/魔力/时魔估算）。"
    plugin_icon = (
        "https://raw.githubusercontent.com/jxxghp/MoviePilot-Frontend/refs/heads/v2/src/assets/images/misc/statistic.png"
    )
    plugin_version = "1.3.1"
    plugin_label = "站点,做种,统计"
    plugin_author = "miguelito39721"
    plugin_config_prefix = "seedstats_"
    plugin_order = 26
    auth_level = 1

    _enabled: bool = False
    _downloaders: List[str] = []
    _dashboard: bool = True
    _interval: int = 60
    _refreshing: bool = False
    # 站点域名前缀到站点名的兜底映射
    _site_prefixes: Dict[str, str] = {}

    def init_plugin(self, config: Optional[Dict[str, Any]] = None) -> None:
        """根据插件配置初始化运行状态，并安排一次立即统计。"""
        self.stop_service()
        self._enabled = False
        self._downloaders = []
        self._dashboard = True
        self._interval = 60
        if config:
            self._enabled = bool(config.get("enabled"))
            self._downloaders = [str(name) for name in (config.get("downloaders") or []) if name]
            self._dashboard = bool(config.get("dashboard", True))
            self._interval = max(int(config.get("interval") or 60), 5)
        if self._enabled:
            self.__schedule_once()

    def get_state(self) -> bool:
        """返回插件是否已启用。"""
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        """返回插件远程命令列表（本插件无需命令）。"""
        return []

    def get_api(self) -> List[Dict[str, Any]]:
        """返回插件 API 列表（本插件无需额外 API）。"""
        return []

    def get_service(self) -> Optional[List[Dict[str, Any]]]:
        """注册后台定时刷新统计缓存的服务。"""
        if not self._enabled:
            return []
        return [
            {
                "id": f"{self.__class__.__name__}Refresh",
                "name": "站点保种统计刷新",
                "trigger": "interval",
                "func": self.__refresh_cache,
                "kwargs": {"minutes": self._interval}
            }
        ]

    def get_form(self) -> Tuple[Optional[List[dict]], Dict[str, Any]]:
        """返回插件配置表单与默认配置。"""
        downloader_items = [{"title": name, "value": name}
                            for name in (DownloaderHelper().get_configs() or {}).keys()]
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {"component": "VSwitch",
                                     "props": {"model": "enabled", "label": "启用插件"}}
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {"component": "VSwitch",
                                     "props": {"model": "dashboard", "label": "显示首页仪表板"}}
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {"component": "VTextField",
                                     "props": {"model": "interval", "label": "刷新间隔(分钟)",
                                               "placeholder": "60"}}
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {"cols": 12, "md": 3},
                                "content": [
                                    {"component": "VSelect",
                                     "props": {"model": "downloaders", "label": "统计的下载器",
                                               "multiple": True, "chips": True, "clearable": True,
                                               "hint": "不选则统计全部已启用下载器",
                                               "persistentHint": True, "items": downloader_items}}
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {"cols": 12},
                                "content": [
                                    {"component": "VAlert",
                                     "props": {"type": "info", "variant": "tonal",
                                               "text": "只读插件：统计在后台线程定时计算并缓存，页面/仪表板读缓存秒出。"
                                                       "账户信息取自 MoviePilot 站点数据（上传/下载/分享率/等级/魔力）；"
                                                       "「时魔*」为根据相邻两次站点数据快照的魔力增量估算，非站点官方数值。"
                                                       "保存配置后会立即重新统计一次。"}}
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "dashboard": True,
            "interval": 60,
            "downloaders": []
        }

    def get_page(self) -> Optional[List[dict]]:
        """返回插件详情页面（读取缓存快照）。"""
        if not self._enabled:
            return [
                {"component": "VAlert",
                 "props": {"type": "warning", "variant": "tonal", "text": "插件未启用，请先在配置中启用。"}}
            ]
        cached = self.__cached()
        rows = cached.get("rows") or []
        totals = cached.get("totals") or {}
        if not rows:
            return [
                {"component": "VAlert",
                 "props": {"type": "info", "variant": "tonal",
                           "text": "首次统计进行中，请稍等十几秒后重新打开本页面。"}}
            ]

        top_rows = rows[:12]
        cross_seed = totals.get("辅种", 0)
        normal_seed = max(totals.get("做种", 0) - cross_seed, 0)
        bar_options = {
            "chart": {"type": "bar", "toolbar": {"show": False}},
            "plotOptions": {"bar": {"horizontal": True, "borderRadius": 4}},
            "xaxis": {"categories": [row.get("站点") for row in top_rows]},
            "legend": {"show": False},
            "noData": {"text": "暂无数据"},
        }
        bar_series = [{"name": "做种数", "data": [row.get("做种", 0) for row in top_rows]}]
        pie_options = {
            "chart": {"type": "pie"},
            "labels": ["辅种任务", "普通做种"],
            "legend": {"show": True},
            "noData": {"text": "暂无数据"},
        }

        headers = ("站点", "做种", "辅种", "上传", "下载", "分享率", "等级", "魔力", "时魔*", "数据时间")
        return [
            {
                "component": "VRow",
                "content": [
                    self.__card("站点数", str(len(rows)), "mdi-server-network", 6, 2),
                    self.__card("任务总数", str(totals.get("任务数", 0)), "mdi-database", 6, 2),
                    self.__card("做种中", str(totals.get("做种", 0)), "mdi-upload", 6, 2),
                    self.__card("辅种任务", str(cross_seed), "mdi-content-duplicate", 6, 2),
                    self.__card("总上传", self.__format_size(totals.get("上传", 0)), "mdi-cloud-upload", 6, 2),
                    self.__card("总下载", self.__format_size(totals.get("下载", 0)), "mdi-cloud-download", 6, 2),
                ]
            },
            {
                "component": "VRow",
                "props": {"class": "mt-2"},
                "content": [
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 7},
                        "content": [
                            {"component": "VCard",
                             "props": {"variant": "tonal"},
                             "content": [
                                 {"component": "VCardTitle", "text": "做种数 Top 12"},
                                 {"component": "VCardText",
                                  "content": [{"component": "VApexChart",
                                               "props": {"height": 380, "options": bar_options,
                                                         "series": bar_series}}]}
                             ]}
                        ]
                    },
                    {
                        "component": "VCol",
                        "props": {"cols": 12, "md": 5},
                        "content": [
                            {"component": "VCard",
                             "props": {"variant": "tonal"},
                             "content": [
                                 {"component": "VCardTitle", "text": "辅种占比"},
                                 {"component": "VCardText",
                                  "content": [{"component": "VApexChart",
                                               "props": {"height": 380, "options": pie_options,
                                                         "series": [cross_seed, normal_seed]}}]}
                             ]}
                        ]
                    }
                ]
            },
            {
                "component": "VCard",
                "props": {"variant": "tonal", "class": "mt-3"},
                "content": [
                    {"component": "VCardTitle",
                     "text": f"各站点明细（统计时间：{cached.get('timestamp', '未知')}）"},
                    {"component": "VCardText", "props": {"class": "text-caption text-medium-emphasis"},
                     "text": "时魔* = 相邻两次站点数据快照的魔力增量 ÷ 时间（非站点官方数值，仅供参考）"},
                    {"component": "VTable",
                     "props": {"density": "compact", "hover": True},
                     "content": [
                         {"component": "thead",
                          "content": [{"component": "tr",
                                       "content": [{"component": "th", "text": text} for text in headers]}]},
                         {"component": "tbody",
                          "content": [self.__row(row) for row in rows]}
                     ]}
                ]
            }
        ]

    def get_dashboard_meta(self) -> Optional[List[Dict[str, str]]]:
        """返回插件仪表板元信息。"""
        if not self._enabled or not self._dashboard:
            return []
        return [{"key": "seedstats", "name": "站点保种统计"}]

    def get_dashboard(
        self, key: str, **kwargs: Any
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any], Optional[List[Dict[str, Any]]]]]:
        """返回首页仪表板配置与缓存数据。"""
        if not self._enabled or not self._dashboard:
            return None
        cached = self.__cached()
        rows = cached.get("rows") or []
        totals = cached.get("totals") or {}
        cols = {"cols": 12, "md": 6}
        attrs = {"refresh": 600, "title": "站点保种统计"}
        if not rows:
            return cols, attrs, [
                {"component": "VAlert",
                 "props": {"type": "info", "variant": "tonal", "text": "首次统计进行中，稍后自动刷新"}}
            ]
        top_rows = rows[:10]
        bar_options = {
            "chart": {"type": "bar", "toolbar": {"show": False}},
            "plotOptions": {"bar": {"horizontal": True, "borderRadius": 4}},
            "xaxis": {"categories": [row.get("站点") for row in top_rows]},
            "legend": {"show": False},
            "noData": {"text": "暂无数据"},
        }
        return cols, attrs, [
            {
                "component": "VRow",
                "content": [
                    self.__card("做种中", str(totals.get("做种", 0)), "mdi-upload", 6, 3),
                    self.__card("辅种任务", str(totals.get("辅种", 0)), "mdi-content-duplicate", 6, 3),
                    self.__card("总上传", self.__format_size(totals.get("上传", 0)), "mdi-cloud-upload", 6, 3),
                    self.__card("总下载", self.__format_size(totals.get("下载", 0)), "mdi-cloud-download", 6, 3),
                ]
            },
            {
                "component": "VApexChart",
                "props": {"height": 320, "options": bar_options,
                          "series": [{"name": "做种数", "data": [row.get("做种", 0) for row in top_rows]}]}
            },
            {
                "component": "div",
                "props": {"class": "text-caption text-medium-emphasis mt-2"},
                "text": f"共 {len(rows)} 个站点 ｜ 统计时间 {cached.get('timestamp', '未知')}"
            }
        ]

    def stop_service(self) -> None:
        """停止插件服务，取消待执行的首次统计任务。"""
        try:
            from app.sdk.scheduler import remove_plugin_once_job

            remove_plugin_once_job(self.__class__.__name__, f"{self.__class__.__name__}Once")
        except Exception:  # noqa: BLE001
            pass
        return None

    def __schedule_once(self) -> None:
        """安排一次立即统计，用于启用或保存配置后快速出数据。"""
        try:
            from app.sdk.scheduler import add_plugin_once_job

            add_plugin_once_job(
                plugin_id=self.__class__.__name__,
                job_id=f"{self.__class__.__name__}Once",
                func=self.__refresh_cache,
                name="站点保种统计首次刷新",
                delay_seconds=5,
            )
        except Exception as err:  # noqa: BLE001
            logger.error(f"站点保种统计：安排首次统计失败 {err}")

    def __refresh_cache(self) -> None:
        """重新计算统计结果并写入缓存。"""
        if self._refreshing:
            logger.info("站点保种统计：上一次统计尚未结束，本次跳过")
            return
        self._refreshing = True
        started = time.time()
        try:
            rows, totals = self.__collect_stats()
            self.save_data(_CACHE_KEY, {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "rows": rows,
                "totals": totals,
            })
            logger.info(f"站点保种统计：统计完成，站点 {len(rows)} 个，任务 {totals.get('任务数', 0)} 个，"
                        f"用时 {time.time() - started:.1f}s")
        except Exception as err:  # noqa: BLE001
            logger.error(f"站点保种统计：统计失败 {err}")
        finally:
            self._refreshing = False

    def __cached(self) -> Dict[str, Any]:
        """读取缓存的统计快照。"""
        data = self.get_data(_CACHE_KEY)
        return data if isinstance(data, dict) else {}

    def __card(self, title: str, value: str, icon: str, cols: int, md: int) -> Dict[str, Any]:
        """构造一个统计卡片元素。"""
        return {
            "component": "VCol",
            "props": {"cols": cols, "md": md},
            "content": [
                {"component": "VCard",
                 "props": {"variant": "tonal"},
                 "content": [
                     {"component": "VCardText",
                      "props": {"class": "d-flex align-center"},
                      "content": [
                          {"component": "VIcon", "props": {"icon": icon, "size": 32, "class": "me-3",
                                                            "color": "primary"}},
                          {"component": "div",
                           "content": [
                               {"component": "div", "props": {"class": "text-caption text-medium-emphasis"},
                                "text": title},
                               {"component": "div", "props": {"class": "text-h6 font-weight-bold"},
                                "text": value}
                           ]}
                      ]}
                 ]}
            ]
        }

    def __row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """构造站点明细表的一行。"""
        cells = [
            {"component": "td", "props": {"class": "font-weight-medium"}, "text": str(row.get("站点") or "-")},
            {"component": "td", "text": str(row.get("做种", 0))},
            {"component": "td", "props": {"class": "text-info"}, "text": str(row.get("辅种", 0))},
            {"component": "td", "props": {"class": "text-success"},
             "text": self.__format_size(row.get("上传"))},
            {"component": "td", "props": {"class": "text-error"}, "text": self.__format_size(row.get("下载"))},
            {"component": "td", "text": self.__format_ratio(row.get("分享率"))},
            {"component": "td", "text": str(row.get("等级") or "-")},
            {"component": "td", "text": self.__format_bonus(row.get("魔力"))},
            {"component": "td", "props": {"class": "text-primary"}, "text": self.__format_hourly(row.get("时魔"))},
            {"component": "td", "props": {"class": "text-medium-emphasis"},
             "text": str(row.get("数据时间") or "-")},
        ]
        return {"component": "tr", "content": cells}

    @staticmethod
    def __format_size(value: Any) -> str:
        """把字节数格式化为可读容量。"""
        try:
            size = float(value or 0)
        except (TypeError, ValueError):
            return "-"
        if size <= 0:
            return "-"
        for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
            if size < 1024 or unit == "PB":
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
            size /= 1024
        return "-"

    @staticmethod
    def __format_bonus(value: Any) -> str:
        """格式化魔力值。"""
        try:
            bonus = float(value or 0)
        except (TypeError, ValueError):
            return "-"
        if bonus <= 0:
            return "-"
        if bonus >= 10000:
            return f"{bonus / 10000:.2f} 万"
        return f"{bonus:,.0f}"

    @staticmethod
    def __format_ratio(value: Any) -> str:
        """格式化分享率。"""
        try:
            ratio = float(value or 0)
        except (TypeError, ValueError):
            return "-"
        if ratio <= 0:
            return "-"
        if ratio >= 1000:
            return "∞"
        return f"{ratio:.2f}"

    @staticmethod
    def __format_hourly(value: Any) -> str:
        """格式化估算时魔。"""
        try:
            hourly = float(value)
        except (TypeError, ValueError):
            return "-"
        return f"{hourly:.1f}/时"

    def __collect_stats(self) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """读取下载器任务与站点账户数据，按站点汇总。"""
        summary: Dict[str, Dict[str, Any]] = {}
        totals = {"下载器": 0, "任务数": 0, "做种": 0, "辅种": 0, "上传": 0, "下载": 0}
        accounts = self.__load_accounts()
        self.__load_site_prefixes()
        try:
            services = DownloaderHelper().get_services(name_filters=self._downloaders or None) or {}
        except Exception as err:  # noqa: BLE001
            logger.error(f"站点保种统计：获取下载器失败 {err}")
            return [], totals
        sites_helper: Optional[SitesHelper] = None
        try:
            sites_helper = SitesHelper()
        except Exception as err:  # noqa: BLE001
            logger.error(f"站点保种统计：初始化站点助手失败 {err}")
        for service in services.values():
            totals["下载器"] += 1
            torrents: Optional[List[Any]] = None
            # 优先使用下载器原生接口的轻量字段读取，显著降低耗时；失败时回退到公共接口
            native = getattr(service.instance, "trc", None)
            if native is not None:
                try:
                    torrents = native.get_torrents(arguments=["hashString", "status", "percentDone",
                                                              "labels", "downloadDir", "trackers"])
                except Exception as err:  # noqa: BLE001
                    logger.error(f"站点保种统计：{service.name} 原生快速读取失败，回退公共接口 {err}")
                    torrents = None
            if torrents is None:
                try:
                    torrents, error = service.instance.get_torrents()
                except Exception as err:  # noqa: BLE001
                    logger.error(f"站点保种统计：读取下载器 {service.name} 任务失败 {err}")
                    continue
                if error:
                    torrents = None
            if not torrents:
                continue
            for torrent in torrents:
                site = self.__resolve_site(torrent=torrent, sites_helper=sites_helper)
                entry = summary.setdefault(site, {"任务数": 0, "做种": 0, "暂停": 0, "其他": 0, "辅种": 0})
                entry["任务数"] += 1
                state = str(self.__field(torrent, "status") or "").lower()
                if state in _SEEDING_STATES:
                    entry["做种"] += 1
                elif state in _PAUSED_STATES:
                    entry["暂停"] += 1
                else:
                    entry["其他"] += 1
                if _CROSS_SEED_TAG in self.__labels(torrent):
                    entry["辅种"] += 1
        rows: List[Dict[str, Any]] = []
        for site, entry in summary.items():
            row: Dict[str, Any] = {"站点": site}
            row.update(entry)
            account = accounts.get(site) or {}
            row.update({
                "上传": account.get("上传"),
                "下载": account.get("下载"),
                "分享率": account.get("分享率"),
                "等级": account.get("等级"),
                "魔力": account.get("魔力"),
                "时魔": account.get("时魔"),
                "数据时间": account.get("数据时间"),
            })
            rows.append(row)
        # 站点数据里有、但本地没有做种的站点也一并展示
        for site, account in accounts.items():
            if site in summary:
                continue
            rows.append({
                "站点": site, "任务数": 0, "做种": 0, "暂停": 0, "其他": 0, "辅种": 0,
                "上传": account.get("上传"), "下载": account.get("下载"), "分享率": account.get("分享率"),
                "等级": account.get("等级"), "魔力": account.get("魔力"), "时魔": account.get("时魔"),
                "数据时间": account.get("数据时间"),
            })
        rows.sort(key=lambda item: (item["任务数"], item.get("上传") or 0), reverse=True)
        for row in rows:
            totals["任务数"] += row["任务数"]
            totals["做种"] += row["做种"]
            totals["辅种"] += row["辅种"]
            totals["上传"] += float(row.get("上传") or 0)
            totals["下载"] += float(row.get("下载") or 0)
        return rows, totals

    def __load_accounts(self) -> Dict[str, Dict[str, Any]]:
        """读取各站点最新账户数据，并估算实际魔力增速（时魔）。"""
        accounts: Dict[str, Dict[str, Any]] = {}
        try:
            site_oper = SiteOper()
            latest: List[SiteUserData] = site_oper.get_userdata_latest() or []
        except Exception as err:  # noqa: BLE001
            logger.error(f"站点保种统计：读取站点数据失败 {err}")
            return accounts
        previous_cache: Dict[str, Dict[str, SiteUserData]] = {}
        for data in latest:
            if not data or not data.name:
                continue
            hourly: Optional[float] = None
            try:
                hourly = self.__estimate_hourly(site_oper=site_oper, data=data,
                                                previous_cache=previous_cache)
            except Exception as err:  # noqa: BLE001
                logger.error(f"站点保种统计：估算 {data.name} 时魔失败 {err}")
            accounts[str(data.name)] = {
                "上传": data.upload,
                "下载": data.download,
                "分享率": data.ratio,
                "等级": data.user_level,
                "魔力": data.bonus,
                "时魔": hourly,
                "数据时间": f"{data.updated_day or ''} {data.updated_time or ''}".strip(),
            }
        return accounts

    @staticmethod
    def __estimate_hourly(site_oper: SiteOper, data: SiteUserData,
                          previous_cache: Dict[str, Dict[str, SiteUserData]]) -> Optional[float]:
        """按相邻快照的魔力增量估算时魔。"""
        if not data.updated_day or data.bonus is None:
            return None
        try:
            today = datetime.strptime(f"{data.updated_day} {data.updated_time or '00:00:00'}",
                                      "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
        for back in range(1, 4):
            prev_day = (today - timedelta(days=back)).strftime("%Y-%m-%d")
            if prev_day not in previous_cache:
                previous_cache[prev_day] = {
                    str(row.name): row for row in (site_oper.get_userdata_by_date(prev_day) or []) if row
                }
            previous = previous_cache[prev_day].get(str(data.name))
            if not previous or previous.bonus is None:
                continue
            try:
                prev_time = datetime.strptime(f"{previous.updated_day} {previous.updated_time or '00:00:00'}",
                                              "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            hours = (today - prev_time).total_seconds() / 3600
            if hours <= 0 or hours > _MAX_HOURLY_WINDOW:
                continue
            delta = float(data.bonus or 0) - float(previous.bonus or 0)
            if delta < 0:
                continue
            return delta / hours
        return None

    def __load_site_prefixes(self) -> None:
        """加载已配置站点的域名前缀映射，用于 tracker 归属兜底匹配。"""
        self._site_prefixes = {}
        try:
            sites = SiteOper().list_order_by_pri() or []
        except Exception as err:  # noqa: BLE001
            logger.error(f"站点保种统计：读取站点列表失败 {err}")
            return
        for site in sites:
            domain = str(getattr(site, "domain", "") or "").lower()
            name = str(getattr(site, "name", "") or "")
            if not domain or not name:
                continue
            self._site_prefixes[domain] = name
            self._site_prefixes[domain.split(".")[0]] = name

    def __resolve_site(self, torrent: Any, sites_helper: Optional[SitesHelper]) -> str:
        """根据任务的 tracker 解析所属站点名称。"""
        trackers = self.__field(torrent, "trackers") or []
        primary = None
        for tracker in trackers:
            if self.__field(tracker, "tier") == 0:
                primary = tracker
                break
        if primary is None and trackers:
            primary = trackers[0]
        if primary is None:
            return "未识别"
        announce = self.__field(primary, "announce") or ""
        site_name = self.__field(primary, "sitename") or ""
        host = str(self.__field(primary, "host") or "")
        domain = ""
        if announce:
            domain = StringUtils.get_url_domain(str(announce)).split(":")[0]
        for candidate in (domain, host):
            if not candidate:
                continue
            try:
                indexer = sites_helper.get_indexer(candidate) or {}
            except Exception:  # noqa: BLE001
                indexer = {}
            if indexer.get("name"):
                return str(indexer["name"])
        # 兜底：按已配置站点的域名前缀匹配
        for candidate in (domain, host):
            key = str(candidate).split(":")[0].lower()
            if not key:
                continue
            for prefix in (key, key.split(".")[0], key.replace("tracker.", "")):
                if prefix in self._site_prefixes:
                    return self._site_prefixes[prefix]
        return str(site_name or host or domain or "未识别")

    @staticmethod
    def __field(obj: Any, name: str) -> Any:
        """兼容字典与对象两种形式的字段读取。"""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    @classmethod
    def __labels(cls, torrent: Any) -> List[str]:
        """读取任务的标签列表。"""
        labels = cls.__field(torrent, "labels")
        if labels is None:
            labels = cls.__field(torrent, "tags")
        if not labels:
            return []
        if isinstance(labels, str):
            return [item.strip() for item in labels.split(",") if item.strip()]
        return [str(item).strip() for item in labels]
