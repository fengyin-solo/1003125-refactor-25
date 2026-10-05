"""导出通道：所有业务模块共用的一份导出实现。

每个模块在自己的 router 上调用 register_export 一次，把 GET /export 挂到模块前缀下；
调用必须排在 /{entry_id} 定义之前，否则导出请求会被单条路由按编号解析，直接 422。

导出与列表取自同一份取数口径：字段用模块的 LIST_FIELDS，条件（keyword/status）
原样透传给列表在用的 service.list_entries，导出内容就是当前条件下列表的全量。
"""
from __future__ import annotations

import csv
import io
from typing import Any, Callable

from fastapi import APIRouter, Query
from fastapi.responses import Response

# 导出不分页，一次取全量；上限单独放宽，不受列表接口每页 200 条的限制
EXPORT_PAGE_SIZE = 10000

ListEntries = Callable[..., tuple[list[dict[str, Any]], int]]


def register_export(
    router: APIRouter,
    *,
    module: str,
    fields: list[str],
    statuses: list[str],
    list_entries: ListEntries,
    keyword_description: str,
) -> None:
    """把 GET /export 注册到模块 router 上；每个模块只调用一次。"""

    @router.get("/export", operation_id=f"export_{module}")
    def export_entries(
        keyword: str | None = Query(default=None, description=keyword_description),
        status: str | None = Query(default=None, description="、".join(statuses)),
    ) -> Response:
        """按当前条件导出清单：条件与列表接口同口径，字段与列表列一致。"""
        items, _total = list_entries(keyword=keyword, status=status, page=1, size=EXPORT_PAGE_SIZE)
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(fields)
        for item in items:
            writer.writerow([item.get(field, "") for field in fields])
        return Response(
            content=buffer.getvalue().encode("utf-8-sig"),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{module}-export.csv"'},
        )
