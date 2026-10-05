"""监测分站接口：维护监测分站，覆盖通信排查、切换供电、办理停用等动作。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.exporting import register_export
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.monitorstation import MonitorstationService

router = APIRouter(prefix="/api/monitorstation", tags=["监测分站"])

service = MonitorstationService()

LIST_FIELDS = ["分站编号", "分站名称", "所在位置", "通信地址", "接入传感器", "信号强度", "后备电源", "分站状态"]
STATUSES = ["正常运行", "通信中断", "备用供电", "已停用"]

# 导出路径要排在 /{entry_id} 之前注册，否则会被按编号取单条的路由接走
register_export(router, service=service, fields=LIST_FIELDS)


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按分站编号检索"),
    status: str | None = Query(default=None, description="正常运行、通信中断、备用供电、已停用"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按分站编号与状态过滤监测分站列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条监测分站明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"监测分站 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条监测分站，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="监测分站已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条监测分站执行通信排查、切换供电、办理停用；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
