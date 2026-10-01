"""Framework-neutral dashboard API adapter for SCHOOL OS V11.8.

The application layer can map these functions to FastAPI, Flask, Django, or
another HTTP framework without duplicating authorization logic.
"""
from __future__ import annotations
from sqlalchemy.orm import Session as DBSession
from security.auth import Session
from services.dashboard_service import dashboard_summary


def dashboard_endpoint(db: DBSession, session: Session, school_id: int, trimestre: str | None = None) -> dict:
    """Return dashboard data only after tenant/permission checks."""
    return dashboard_summary(db, session, school_id=school_id, trimestre=trimestre)
