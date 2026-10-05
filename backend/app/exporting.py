"""导出通道的共用实现：二十个模块共用这一份，按模块各自注册一次。

导出的字段与过滤条件和列表接口保持同一份取数口径：都走
``service.list_entries``，查询参数也与列表接口一致（keyword、status）。
"""
from __future__ import annotations

import csv
import io
from typing import Any, Protocol

from fastapi import APIRouter, Query, Response

# 导出不分页，一次取全量；上限与列表接口的页大小约束互不干扰
EXPORT_LIMIT = 10000


class ListService(Protocol):
    """各模块 service 的列表取数口径，导出与列表共用这一套过滤条件。"""

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]: ...


def register_export(router: APIRouter, *, service: ListService, fields: list[str]) -> None:
    """把导出路径挂到模块路由上。

    必须在 ``/{entry_id}`` 单条路由之前调用：FastAPI 按注册顺序匹配，
    否则 /export 会被单条路由接走，按 int 解析 entry_id 直接报参数错误。
    """
    module = router.prefix.rsplit("/", 1)[-1]

    @router.get("/export", operation_id=f"export_{module}")
    def export_entries(
        keyword: str | None = Query(default=None, description="与列表一致的编号检索"),
        status: str | None = Query(default=None, description="与列表一致的状态过滤"),
    ) -> Response:
        """导出当前过滤条件下的清单；字段、条件与列表接口同一份口径。"""
        items, _total = service.list_entries(keyword=keyword, status=status, page=1, size=EXPORT_LIMIT)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(fields)
        for item in items:
            writer.writerow(["" if item.get(field) is None else item.get(field) for field in fields])
        # 带 BOM 的 UTF-8，保证 Excel 直接打开中文不乱码
        content = "\ufeff" + buffer.getvalue()
        return Response(
            content=content.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{module}-export.csv"'},
        )
