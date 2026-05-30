from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, get_request_context, require_roles
from app.core.database import get_db_session
from app.domains.dashboard.service import DashboardAggregationService
from app.domains.shared.schemas import (
    ListResponse,
    decode_offset_cursor,
    encode_offset_cursor,
    paginated_response,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary(
    context: Annotated[RequestContext, Depends(get_request_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = DashboardAggregationService(session)
    return await service.get_summary(
        organization_id=context.organization_id,
        role=context.role,
    )


@router.get("/charts")
async def get_charts(
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = DashboardAggregationService(session)
    return await service.get_chart_series(organization_id=context.organization_id)


@router.get("/alerts", response_model=ListResponse[dict])
async def list_sla_alerts(
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: str | None = None,
) -> dict:
    service = DashboardAggregationService(session)
    offset = decode_offset_cursor(cursor)
    items = await service.list_sla_alerts(
            organization_id=context.organization_id,
            status=status,
            limit=limit + 1,
            offset=offset,
        )
    return paginated_response(
        items,
        limit=limit,
        sort="-breached_at",
        offset=offset,
        next_cursor=encode_offset_cursor(offset + limit),
    )


@router.post("/reconcile")
async def reconcile_dashboard_read_models(
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = DashboardAggregationService(session)
    return await service.queue_reconciliation(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
    )


@router.get("/admin")
async def get_admin_dashboard(
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = DashboardAggregationService(session)
    return await service.get_role_dashboard(
        organization_id=context.organization_id,
        role=context.role,
        focus="tenant operations, audit, users and workload",
    )


@router.get("/employee")
async def get_employee_dashboard(
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = DashboardAggregationService(session)
    return await service.get_role_dashboard(
        organization_id=context.organization_id,
        role=context.role,
        focus="assigned customers, open incidents and appointments",
    )


@router.get("/customer")
async def get_customer_dashboard(
    context: Annotated[RequestContext, Depends(require_roles("admin", "customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = DashboardAggregationService(session)
    return await service.get_role_dashboard(
        organization_id=context.organization_id,
        role=context.role,
        focus="active policies, incident reports and support messages",
    )
