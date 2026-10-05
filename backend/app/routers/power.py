"""供电系统接口：维护供电设备，覆盖负荷预警、绝缘报警、安排修复等动作。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.exporting import register_export
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.power import PowerService

router = APIRouter(prefix="/api/power", tags=["供电系统"])

service = PowerService()

LIST_FIELDS = ["设备编号", "设备类型", "电压等级", "所属区域", "运行负荷", "绝缘电阻", "上次试验", "设备状态"]
STATUSES = ["正常", "负荷过高", "绝缘降低", "已修复"]

# 导出路径要排在 /{entry_id} 之前注册，否则会被按编号取单条的路由接走
register_export(router, service=service, fields=LIST_FIELDS)


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按设备编号检索"),
    status: str | None = Query(default=None, description="正常、负荷过高、绝缘降低、已修复"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按设备编号与状态过滤供电系统列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条供电设备明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"供电设备 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条供电设备，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="供电设备已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条供电设备执行负荷预警、绝缘报警、安排修复；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
