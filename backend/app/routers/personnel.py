"""人员定位接口：维护定位终端，覆盖记录离线、低电提醒、办理更换等动作。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.routers.export import register_export
from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.personnel import PersonnelService

router = APIRouter(prefix="/api/personnel", tags=["人员定位"])

service = PersonnelService()

LIST_FIELDS = ["终端编号", "携带人员", "所在位置", "入井时刻", "区域停留", "定位精度", "信号强度", "终端状态"]
STATUSES = ["在线", "离线", "低电量", "已更换"]

# 导出要在单条路由之前注册，否则 /export 会被 /{entry_id} 按编号接走
register_export(
    router,
    module="personnel",
    fields=LIST_FIELDS,
    statuses=STATUSES,
    list_entries=service.list_entries,
    keyword_description="按终端编号检索",
)


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按终端编号检索"),
    status: str | None = Query(default=None, description="在线、离线、低电量、已更换"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按终端编号与状态过滤人员定位列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条定位终端明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"定位终端 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条定位终端，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="定位终端已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条定位终端执行记录离线、低电提醒、办理更换；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)

