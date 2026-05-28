"""Import all SQLAlchemy models so Alembic can discover metadata."""

from app.domains.dashboard.models import SlaAlert, SlaRule  # noqa: F401
from app.domains.ai.models import (  # noqa: F401
    AiProviderCall,
    ChatMessage,
    ChatSession,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.domains.insurance.models import (  # noqa: F401
    InsuranceAppointment,
    InsuranceClaimTransition,
    InsuranceConversation,
    InsuranceCustomer,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
    InsuranceMessage,
    InsurancePlan,
    InsurancePolicy,
    InsuranceWorkflow,
)
from app.domains.platform.models import (  # noqa: F401
    AuditEvent,
    LoginEvent,
    Membership,
    Organization,
    Permission,
    Role,
    RolePermission,
    User,
)
from app.domains.shared.models import BackgroundJob, FileAsset  # noqa: F401
