"""插件 API 路由定义：Bearer 认证，供联邦前端调用。"""

from __future__ import annotations

from typing import Any, Dict, List


def build_api_routes(owner: Any) -> List[Dict[str, Any]]:
    """构建插件 API 路由清单。"""
    return [
        {
            "path": "/status",
            "endpoint": owner.engine_status,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "读取音乐标签刮削运行状态与统计",
        },
        {
            "path": "/config",
            "endpoint": owner.engine_config,
            "methods": ["GET"],
            "auth": "bear",
            "summary": "读取插件当前配置",
        },
        {
            "path": "/preview",
            "endpoint": owner.engine_preview,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "试跑：扫描并预览待补全音频（不写文件）",
        },
        {
            "path": "/run",
            "endpoint": owner.engine_run,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "启动音乐标签补全任务",
        },
        {
            "path": "/stop",
            "endpoint": owner.engine_stop,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "停止当前任务",
        },
        {
            "path": "/retry",
            "endpoint": owner.engine_retry,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "重试失败条目",
        },
        {
            "path": "/clear",
            "endpoint": owner.engine_clear,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "清空处理记录与失败清单",
        },
    ]
