from typing import Any

from sqlalchemy.orm import Session

from app.models import AdminUser, AuditLog


def record(
    db: Session,
    actor: AdminUser | None,
    action: str,
    entity_type: str,
    entity_id: object = None,
    **details: Any,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            details=details,
        )
    )
