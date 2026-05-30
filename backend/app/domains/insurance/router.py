from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, get_request_context, require_roles
from app.core.database import get_db_session
from app.core.storage import get_storage_provider, verify_storage_download_token
from app.domains.insurance.assignment_service import InsuranceAssignmentService
from app.domains.insurance.claim_lifecycle_service import ClaimLifecycleService
from app.domains.insurance.correction_service import ClaimCorrectionService
from app.domains.insurance.export_service import ClaimExportService
from app.domains.insurance.customer_policy_service import InsuranceCustomerPolicyService
from app.domains.insurance.incident_service import InsuranceIncidentService
from app.domains.insurance.plan_service import InsurancePlanService
from app.domains.insurance.portal_service import CustomerPortalService
from app.domains.insurance.queue_service import WorkloadQueueService
from app.domains.insurance.support_service import InsuranceSupportService
from app.domains.insurance.schemas import (
    AppointmentOut,
    ClaimDetailOut,
    ClaimTransitionOut,
    ClaimCorrectionOut,
    ExportArtifactOut,
    ExportDownloadOut,
    ConversationDetailOut,
    CreateAssignmentIn,
    CreateAppointmentIn,
    CreateClaimTransitionIn,
    SaveClaimCorrectionIn,
    CreateConversationIn,
    CreateCustomerIn,
    CreateIncidentIn,
    CreateInsurancePlanIn,
    CreateMessageIn,
    CreatePortalAppointmentIn,
    CreatePortalConversationIn,
    CreatePolicyIn,
    CustomerOut,
    CustomerPortalSummaryOut,
    AssignmentOut,
    ConversationOut,
    IncidentOut,
    InsurancePlanOut,
    MessageOut,
    PolicyOut,
    QueueItemOut,
    UpdateQueueItemIn,
)
from app.domains.shared.schemas import (
    ListResponse,
    decode_offset_cursor,
    encode_offset_cursor,
    paginated_response,
)

router = APIRouter(prefix="/insurance", tags=["insurance"])


@router.get("/portal/summary", response_model=CustomerPortalSummaryOut)
async def get_customer_portal_summary(
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = CustomerPortalService(session)
    return await service.get_summary(
        organization_id=context.organization_id,
        user_id=context.user_id,
    )


@router.get("/queues/my", response_model=ListResponse[QueueItemOut])
async def list_my_workload_queue(
    context: Annotated[RequestContext, Depends(require_roles("employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = None,
    priority: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = WorkloadQueueService(session)
    items = await service.list_my_queue(
            organization_id=context.organization_id,
            employee_user_id=context.user_id,
            status=status,
            priority=priority,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="due_at,+priority,-updated_at")


@router.get("/queues", response_model=ListResponse[QueueItemOut])
async def list_admin_workload_queue(
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status: str | None = None,
    priority: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = WorkloadQueueService(session)
    items = await service.list_admin_queue(
            organization_id=context.organization_id,
            status=status,
            priority=priority,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="due_at,+priority,-updated_at")


@router.get("/queues/{item_id}", response_model=QueueItemOut)
async def get_workload_queue_item(
    item_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = WorkloadQueueService(session)
    return await service.get_item(
        organization_id=context.organization_id,
        item_id=item_id,
        actor_user_id=context.user_id,
        role=context.role,
    )


@router.post("/queues/{item_id}/actions", response_model=QueueItemOut)
async def update_workload_queue_item(
    item_id: str,
    payload: UpdateQueueItemIn,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = WorkloadQueueService(session)
    return await service.update_item(
        organization_id=context.organization_id,
        item_id=item_id,
        actor_user_id=context.user_id,
        role=context.role,
        payload=payload,
    )


@router.get("/portal/policies", response_model=ListResponse[PolicyOut])
async def list_customer_portal_policies(
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = CustomerPortalService(session)
    items = await service.list_policies(
            organization_id=context.organization_id,
            user_id=context.user_id,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="-created_at")


@router.get("/portal/incidents", response_model=ListResponse[IncidentOut])
async def list_customer_portal_incidents(
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = CustomerPortalService(session)
    items = await service.list_incidents(
            organization_id=context.organization_id,
            user_id=context.user_id,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="-created_at")


@router.get("/portal/appointments", response_model=ListResponse[AppointmentOut])
async def list_customer_portal_appointments(
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = CustomerPortalService(session)
    items = await service.list_appointments(
            organization_id=context.organization_id,
            user_id=context.user_id,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="scheduled_at")


@router.post("/portal/appointments", response_model=AppointmentOut)
async def request_customer_portal_appointment(
    payload: CreatePortalAppointmentIn,
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = CustomerPortalService(session)
    return await service.request_appointment(
        organization_id=context.organization_id,
        user_id=context.user_id,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.get("/portal/conversations", response_model=ListResponse[ConversationOut])
async def list_customer_portal_conversations(
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = CustomerPortalService(session)
    items = await service.list_conversations(
            organization_id=context.organization_id,
            user_id=context.user_id,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="-created_at")


@router.post("/portal/conversations", response_model=ConversationOut)
async def start_customer_portal_conversation(
    payload: CreatePortalConversationIn,
    context: Annotated[RequestContext, Depends(require_roles("customer"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = CustomerPortalService(session)
    return await service.start_conversation(
        organization_id=context.organization_id,
        user_id=context.user_id,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.get("/claims/{claim_id}", response_model=ClaimDetailOut)
async def get_claim_detail(
    claim_id: str,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = ClaimLifecycleService(session)
    return await service.get_claim_detail(
        organization_id=context.organization_id,
        claim_id=claim_id,
        actor_user_id=context.user_id,
        role=context.role,
    )


@router.get("/claims/{claim_id}/history", response_model=ListResponse[ClaimTransitionOut])
async def list_claim_history(
    claim_id: str,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> dict:
    service = ClaimLifecycleService(session)
    items = await service.list_claim_history(
            organization_id=context.organization_id,
            claim_id=claim_id,
            actor_user_id=context.user_id,
            role=context.role,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="created_at")


@router.post("/claims/{claim_id}/transitions", response_model=ClaimDetailOut)
async def transition_claim(
    claim_id: str,
    payload: CreateClaimTransitionIn,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = ClaimLifecycleService(session)
    return await service.transition_claim(
        organization_id=context.organization_id,
        claim_id=claim_id,
        actor_user_id=context.user_id,
        role=context.role,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.post("/claims/{claim_id}/conversation", response_model=ConversationOut)
async def open_claim_conversation(
    claim_id: str,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = InsuranceSupportService(session)
    return await service.open_claim_conversation(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        role=context.role,
        claim_id=claim_id,
        idempotency_key=idempotency_key,
    )


@router.get("/claims/{claim_id}/corrections", response_model=ListResponse[ClaimCorrectionOut])
async def list_claim_corrections(
    claim_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> dict:
    items = await ClaimCorrectionService(session).list_history(
        organization_id=context.organization_id,
        claim_id=claim_id,
        actor_user_id=context.user_id,
        role=context.role,
        limit=limit + 1,
    )
    return paginated_response(items, limit=limit, sort="-created_at")


@router.post("/claims/{claim_id}/corrections", response_model=ClaimCorrectionOut)
async def save_claim_correction(
    claim_id: str,
    payload: SaveClaimCorrectionIn,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    return await ClaimCorrectionService(session).save_draft(
        organization_id=context.organization_id,
        claim_id=claim_id,
        actor_user_id=context.user_id,
        role=context.role,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.post(
    "/claims/{claim_id}/corrections/{correction_id}/approve",
    response_model=ClaimCorrectionOut,
)
async def approve_claim_correction(
    claim_id: str,
    correction_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    return await ClaimCorrectionService(session).approve(
        organization_id=context.organization_id,
        claim_id=claim_id,
        correction_id=correction_id,
        actor_user_id=context.user_id,
        role=context.role,
        idempotency_key=idempotency_key,
    )


@router.post("/claims/{claim_id}/exports", response_model=ExportArtifactOut)
async def request_claim_export(
    claim_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    return await ClaimExportService(session).request_claim_export(
        organization_id=context.organization_id,
        claim_id=claim_id,
        actor_user_id=context.user_id,
        role=context.role,
    )


@router.get("/exports/{artifact_id}", response_model=ExportArtifactOut)
async def get_export_artifact(
    artifact_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    return await ClaimExportService(session).get_artifact(
        organization_id=context.organization_id,
        artifact_id=artifact_id,
        actor_user_id=context.user_id,
        role=context.role,
    )


@router.get("/exports/{artifact_id}/download", response_model=ExportDownloadOut)
async def create_export_download(
    artifact_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    return await ClaimExportService(session).create_download_reference(
        organization_id=context.organization_id,
        artifact_id=artifact_id,
        actor_user_id=context.user_id,
        role=context.role,
    )


@router.get("/exports/downloads/content")
async def download_export_content(token: str) -> Response:
    _organization_id, storage_key = verify_storage_download_token(token)
    content = await get_storage_provider().get_bytes(storage_key)
    return Response(content=content, media_type="text/csv")


@router.get("/plans", response_model=ListResponse[InsurancePlanOut])
async def list_plans(
    context: Annotated[RequestContext, Depends(get_request_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = InsurancePlanService(session)
    items = await service.list_plans(context.organization_id, limit=limit + 1)
    return paginated_response(items, limit=limit, sort="name")


@router.post("/plans", response_model=InsurancePlanOut)
async def create_plan(
    payload: CreateInsurancePlanIn,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = InsurancePlanService(session)
    return await service.create_plan(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        payload=payload,
    )


@router.get("/customers", response_model=ListResponse[CustomerOut])
async def list_customers(
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = InsuranceCustomerPolicyService(session)
    employee_user_id = context.user_id if context.role == "employee" else None
    items = await service.list_customers(
            context.organization_id,
            employee_user_id=employee_user_id,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="-created_at")


@router.post("/customers", response_model=CustomerOut)
async def create_customer(
    payload: CreateCustomerIn,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = InsuranceCustomerPolicyService(session)
    return await service.create_customer(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        payload=payload,
    )


@router.post("/policies", response_model=PolicyOut)
async def create_policy(
    payload: CreatePolicyIn,
    context: Annotated[RequestContext, Depends(require_roles("admin", "employee"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = InsuranceCustomerPolicyService(session)
    return await service.create_policy(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.get("/policies", response_model=ListResponse[PolicyOut])
async def list_policies(
    context: Annotated[RequestContext, Depends(get_request_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = InsuranceCustomerPolicyService(session)
    items = await service.list_policies(context.organization_id, limit=limit + 1)
    return paginated_response(items, limit=limit, sort="-created_at")


@router.post("/assignments", response_model=AssignmentOut)
async def create_assignment(
    payload: CreateAssignmentIn,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = InsuranceAssignmentService(session)
    return await service.create_assignment(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        payload=payload,
    )


@router.post("/incidents", response_model=IncidentOut)
async def create_incident(
    payload: CreateIncidentIn,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = InsuranceIncidentService(session)
    return await service.create_incident(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        role=context.role,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.get("/incidents", response_model=ListResponse[IncidentOut])
async def list_incidents(
    context: Annotated[RequestContext, Depends(get_request_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = InsuranceIncidentService(session)
    items = await service.list_incidents(context.organization_id, limit=limit + 1)
    return paginated_response(items, limit=limit, sort="-created_at")


@router.post("/appointments", response_model=AppointmentOut)
async def create_appointment(
    payload: CreateAppointmentIn,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = InsuranceSupportService(session)
    return await service.create_appointment(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    payload: CreateConversationIn,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = InsuranceSupportService(session)
    return await service.create_conversation(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        idempotency_key=idempotency_key,
        payload=payload,
    )


@router.get("/conversations", response_model=ListResponse[ConversationOut])
async def list_conversations(
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> dict:
    service = InsuranceSupportService(session)
    items = await service.list_conversations(
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            role=context.role,
            limit=limit + 1,
        )
    return paginated_response(items, limit=limit, sort="-created_at")


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
async def get_conversation_detail(
    conversation_id: str,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = InsuranceSupportService(session)
    return await service.get_conversation_detail(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        role=context.role,
        conversation_id=conversation_id,
        limit=limit,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ListResponse[MessageOut],
)
async def list_conversation_messages(
    conversation_id: str,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: str | None = None,
) -> dict:
    service = InsuranceSupportService(session)
    offset = decode_offset_cursor(cursor)
    items = await service.list_messages(
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            role=context.role,
            conversation_id=conversation_id,
            limit=limit + 1,
            offset=offset,
        )
    return paginated_response(
        items,
        limit=limit,
        sort="created_at",
        offset=offset,
        next_cursor=encode_offset_cursor(offset + limit),
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
async def create_message(
    conversation_id: str,
    payload: CreateMessageIn,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    idempotency_key: Annotated[str, Header(alias="X-Idempotency-Key")],
) -> dict:
    service = InsuranceSupportService(session)
    return await service.create_message(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        role=context.role,
        conversation_id=conversation_id,
        idempotency_key=idempotency_key,
        payload=payload,
    )
