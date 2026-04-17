"""Admin API router for Feature 005."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config import settings
from src.db import get_db
from src.models.admin_user import AdminUser
from src.models.appointment import Appointment, AppointmentStatusEnum
from src.models.dentist import Dentist
from src.models.telegram_user import TelegramUser
from src.models.audit_log import AuditLog, AuditActionEnum, AuditStatusEnum
from src.services.admin_auth_service import AdminAuthService
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Rate limiting (in-memory, per IP)
failed_attempts = {}


def check_rate_limit(ip: str) -> bool:
    """Check if IP is rate limited."""
    now = datetime.now(timezone.utc)
    if ip in failed_attempts:
        attempts, reset_time = failed_attempts[ip]
        if now < reset_time:
            return False
        else:
            del failed_attempts[ip]
    return True


def record_failed_attempt(ip: str):
    """Record failed login attempt."""
    now = datetime.now(timezone.utc)
    if ip not in failed_attempts:
        failed_attempts[ip] = [1, now + timedelta(minutes=15)]
    else:
        attempts, _ = failed_attempts[ip]
        if attempts >= 4:
            failed_attempts[ip] = [5, now + timedelta(minutes=15)]
        else:
            failed_attempts[ip] = [attempts + 1, now + timedelta(minutes=15)]


async def get_current_admin(
    session: AsyncSession = Depends(get_db),
    session_cookie: Optional[str] = Cookie(None, alias="session"),
) -> AdminUser:
    """Dependency to get current admin from session cookie."""
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No session")
    return await AdminAuthService.get_current_admin(session, session_cookie)


# Auth endpoints
@router.post("/auth/login")
async def login(
    request: Request,
    credentials: dict,
    session: AsyncSession = Depends(get_db),
):
    """Login with username/password."""
    ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in 15 minutes.")

    username = credentials.get("username")
    password = credentials.get("password")

    if not username or not password:
        record_failed_attempt(ip)
        raise HTTPException(status_code=400, detail="Missing credentials")

    admin = await AdminAuthService.authenticate(session, username, password)

    if not admin:
        record_failed_attempt(ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Update last login
    admin.last_login_at = datetime.now(timezone.utc)
    await session.commit()

    token = AdminAuthService.create_access_token(admin.id)

    response = JSONResponse({"ok": True, "username": admin.username})
    response.set_cookie(
        "session",
        token,
        httponly=True,
        samesite="lax",
        max_age=settings.admin_jwt_expire_minutes * 60,
        secure=not settings.is_development,
    )
    return response


@router.post("/auth/logout")
async def logout():
    """Logout and clear session cookie."""
    response = JSONResponse({"ok": True})
    response.delete_cookie("session")
    return response


@router.get("/auth/me")
async def get_me(
    admin: AdminUser = Depends(get_current_admin),
):
    """Get current admin."""
    return {"username": admin.username, "id": str(admin.id)}


# Appointments
@router.get("/appointments")
async def list_appointments(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """List appointments with pagination."""
    stmt = select(Appointment).options(
        selectinload(Appointment.patient),
        selectinload(Appointment.dentist),
    )

    if status:
        stmt = stmt.where(Appointment.status == AppointmentStatusEnum(status))

    stmt = stmt.order_by(Appointment.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(stmt)
    appointments = result.unique().scalars().all()

    # Count total
    count_stmt = select(func.count(Appointment.id))
    if status:
        count_stmt = count_stmt.where(Appointment.status == AppointmentStatusEnum(status))
    count_result = await session.execute(count_stmt)
    total = count_result.scalar()

    return {
        "items": [
            {
                "id": str(a.id),
                "patient": {"id": str(a.patient.id), "first_name": a.patient.first_name, "last_name": a.patient.last_name, "telegram_user_id": a.patient.telegram_user_id},
                "dentist": {"id": str(a.dentist.id), "name": a.dentist.name},
                "slot_date": str(a.slot_date),
                "start_time": str(a.start_time),
                "end_time": str(a.end_time),
                "reason": a.reason,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in appointments
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/appointments/{id}")
async def get_appointment(id: str, session: AsyncSession = Depends(get_db)):
    """Get single appointment."""
    stmt = select(Appointment).where(Appointment.id == UUID(id)).options(
        selectinload(Appointment.patient),
        selectinload(Appointment.dentist),
    )
    result = await session.execute(stmt)
    appointment = result.unique().scalars().first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "id": str(appointment.id),
        "patient": {"id": str(appointment.patient.id), "first_name": appointment.patient.first_name, "last_name": appointment.patient.last_name},
        "dentist": {"id": str(appointment.dentist.id), "name": appointment.dentist.name},
        "slot_date": str(appointment.slot_date),
        "start_time": str(appointment.start_time),
        "end_time": str(appointment.end_time),
        "reason": appointment.reason,
        "status": appointment.status.value,
    }


@router.patch("/appointments/{id}/cancel")
async def cancel_appointment(
    id: str,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Cancel appointment."""
    stmt = select(Appointment).where(Appointment.id == UUID(id))
    result = await session.execute(stmt)
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Not found")

    if appointment.status != AppointmentStatusEnum.CONFIRMED:
        raise HTTPException(status_code=409, detail="Appointment is already cancelled")

    appointment.status = AppointmentStatusEnum.CANCELLED
    await session.commit()

    # Audit log
    audit_log = AuditLog(
        user_id=appointment.patient_user_id,
        action=AuditActionEnum.APPOINTMENT_CANCELLED,
        status=AuditStatusEnum.SUCCESS,
        message_text=f"Cancelled by admin {admin.username}",
    )
    session.add(audit_log)
    await session.commit()

    return {"ok": True, "id": str(appointment.id), "status": "cancelled"}


@router.delete("/appointments/{id}")
async def delete_appointment(
    id: str,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Delete appointment."""
    stmt = select(Appointment).where(Appointment.id == UUID(id))
    result = await session.execute(stmt)
    appointment = result.scalars().first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Not found")

    patient_id = appointment.patient_user_id
    await session.delete(appointment)
    await session.commit()

    # Audit log
    audit_log = AuditLog(
        user_id=patient_id,
        action=AuditActionEnum.APPOINTMENT_CANCELLED,
        status=AuditStatusEnum.SUCCESS,
        message_text=f"Deleted by admin {admin.username}",
    )
    session.add(audit_log)
    await session.commit()

    return {"ok": True}


# Dentists
@router.get("/dentists")
async def list_dentists(session: AsyncSession = Depends(get_db)):
    """List dentists."""
    stmt = select(Dentist).order_by(Dentist.name)
    result = await session.execute(stmt)
    dentists = result.scalars().all()

    return {
        "items": [
            {
                "id": str(d.id),
                "name": d.name,
                "calendar_id": d.calendar_id,
                "active_status": d.active_status,
                "created_at": d.created_at.isoformat(),
            }
            for d in dentists
        ]
    }


@router.post("/dentists")
async def create_dentist(
    data: dict,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Create dentist."""
    name = data.get("name")
    calendar_id = data.get("calendar_id")

    if not name or not calendar_id:
        raise HTTPException(status_code=422, detail="Missing required fields")

    dentist = Dentist(name=name, calendar_id=calendar_id, active_status=True)
    session.add(dentist)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=422, detail="Duplicate name or calendar_id")

    # Audit log
    audit_log = AuditLog(
        action=AuditActionEnum.MENU_DISPLAYED,
        status=AuditStatusEnum.SUCCESS,
        message_text=f"Dentist {name} created by admin {admin.username}",
    )
    session.add(audit_log)
    await session.commit()

    return {
        "id": str(dentist.id),
        "name": dentist.name,
        "calendar_id": dentist.calendar_id,
        "active_status": dentist.active_status,
    }


@router.patch("/dentists/{id}")
async def update_dentist(
    id: str,
    data: dict,
    session: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Update dentist."""
    stmt = select(Dentist).where(Dentist.id == UUID(id))
    result = await session.execute(stmt)
    dentist = result.scalars().first()

    if not dentist:
        raise HTTPException(status_code=404, detail="Not found")

    if "name" in data:
        dentist.name = data["name"]
    if "calendar_id" in data:
        dentist.calendar_id = data["calendar_id"]
    if "active_status" in data:
        dentist.active_status = data["active_status"]

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=422, detail="Duplicate name or calendar_id")

    return {
        "id": str(dentist.id),
        "name": dentist.name,
        "calendar_id": dentist.calendar_id,
        "active_status": dentist.active_status,
    }


# Patients
@router.get("/patients")
async def list_patients(
    page: int = 1,
    page_size: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """List patients."""
    stmt = select(TelegramUser).order_by(TelegramUser.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    patients = result.scalars().all()

    # Count total
    count_result = await session.execute(select(func.count(TelegramUser.id)))
    total = count_result.scalar()

    return {
        "items": [
            {
                "id": str(p.id),
                "telegram_user_id": p.telegram_user_id,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "username": p.username,
                "last_interaction": p.created_at.isoformat() if p.created_at else None,
            }
            for p in patients
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/patients/{id}")
async def get_patient(id: str, session: AsyncSession = Depends(get_db)):
    """Get patient with appointments."""
    stmt = select(TelegramUser).where(TelegramUser.id == UUID(id)).options(
        selectinload(TelegramUser.appointments)
    )
    result = await session.execute(stmt)
    patient = result.unique().scalars().first()

    if not patient:
        raise HTTPException(status_code=404, detail="Not found")

    return {
        "id": str(patient.id),
        "telegram_user_id": patient.telegram_user_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "username": patient.username,
        "appointments": [
            {
                "id": str(a.id),
                "dentist": {"id": str(a.dentist_id), "name": a.dentist.name if a.dentist else None},
                "slot_date": str(a.slot_date),
                "status": a.status.value,
            }
            for a in patient.appointments
        ],
    }
