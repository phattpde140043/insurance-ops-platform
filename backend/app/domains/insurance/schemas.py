from pydantic import BaseModel


class InsurancePlanOut(BaseModel):
    id: str
    organization_id: str
    name: str
    premium: int
    status: str
    created_at: str


class CreateInsurancePlanIn(BaseModel):
    name: str
    premium: int
    status: str = "active"


class CustomerOut(BaseModel):
    id: str
    organization_id: str
    name: str
    email: str
    phone: str | None = None
    assigned_employee_id: str | None = None
    created_at: str


class CreateCustomerIn(BaseModel):
    name: str
    email: str
    phone: str | None = None
    assigned_employee_id: str | None = None


class PolicyOut(BaseModel):
    id: str
    organization_id: str
    customer_id: str
    plan_id: str
    status: str
    start_date: str
    created_at: str


class CreatePolicyIn(BaseModel):
    customer_id: str
    plan_id: str
    start_date: str
    status: str = "active"


class IncidentOut(BaseModel):
    id: str
    organization_id: str
    customer_id: str
    incident_type: str
    description: str
    status: str
    claim_state: str = "reported"
    created_at: str


class CreateIncidentIn(BaseModel):
    customer_id: str
    incident_type: str = "medical"
    description: str


class CreateAssignmentIn(BaseModel):
    customer_id: str
    employee_user_id: str
    status: str = "active"


class AssignmentOut(BaseModel):
    id: str
    organization_id: str
    customer_id: str
    employee_user_id: str
    status: str
    created_at: str


class CreateAppointmentIn(BaseModel):
    customer_id: str
    employee_user_id: str
    scheduled_at: str


class CreatePortalAppointmentIn(BaseModel):
    scheduled_at: str


class AppointmentOut(BaseModel):
    id: str
    organization_id: str
    customer_id: str
    employee_user_id: str
    scheduled_at: str
    status: str
    created_at: str


class CreateConversationIn(BaseModel):
    customer_id: str
    employee_user_id: str | None = None
    claim_id: str | None = None


class CreatePortalConversationIn(BaseModel):
    pass


class ConversationOut(BaseModel):
    id: str
    organization_id: str
    customer_id: str
    claim_id: str | None = None
    employee_user_id: str | None = None
    status: str
    created_at: str


class CreateMessageIn(BaseModel):
    body: str
    use_ai: bool = False


class MessageOut(BaseModel):
    id: str
    organization_id: str
    conversation_id: str
    sender_user_id: str | None = None
    role: str = "user"
    body: str
    citations: list[str] = []
    created_at: str


class ConversationDetailOut(ConversationOut):
    messages: list[MessageOut] = []


class CustomerPortalSummaryOut(BaseModel):
    customer: CustomerOut
    policies: list[PolicyOut]
    recent_incidents: list[IncidentOut]
    upcoming_appointments: list[AppointmentOut]
    open_conversations: list[ConversationOut]


class QueueItemOut(BaseModel):
    id: str
    item_type: str
    source_id: str
    organization_id: str
    customer_id: str
    employee_user_id: str | None = None
    status: str
    priority: str
    due_at: str | None = None
    created_at: str


class UpdateQueueItemIn(BaseModel):
    status: str | None = None
    priority: str | None = None
    employee_user_id: str | None = None


class ClaimDetailOut(IncidentOut):
    allowed_transitions: list[str] = []


class CreateClaimTransitionIn(BaseModel):
    to_state: str
    reason: str


class ClaimTransitionOut(BaseModel):
    id: str
    organization_id: str
    claim_id: str
    actor_user_id: str
    from_state: str | None = None
    to_state: str
    reason: str
    created_at: str
