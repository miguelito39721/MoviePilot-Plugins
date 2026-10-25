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
        {
            "path": "/duplicates",
            "endpoint": owner.engine_duplicates,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "扫描重复音频：完全重复与同曲不同版本（只读）",
        },
        {
            "path": "/duplicates/result",
            "endpoint": owner.engine_duplicates_result,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "读取后台查重任务状态与最近结果",
        },
        {
            "path": "/duplicates/quarantine",
            "endpoint": owner.engine_quarantine,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "把选中的重复文件移入隔离目录（可还原）",
        },
        {
            "path": "/duplicates/restore",
            "endpoint": owner.engine_restore_quarantine,
            "methods": ["POST"],
            "auth": "bear",
            "summary": "把隔离目录中的文件还原到原路径",
        },
    ]
