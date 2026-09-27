"""FastAPI routes for Multi-Tenant Auth, Profile, Persona, Memory & Reporting."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from src.platform.auth import (
    get_current_user_and_profile,
    login_user,
    logout_user,
    register_user,
)
from src.platform.memory import ProfileMemoryService
from src.platform.models import (
    AuthResponse,
    LoginRequest,
    MemoryCreate,
    MemoryOut,
    PersonaCreate,
    PersonaGenerateRequest,
    PersonaOut,
    PersonaUpdate,
    ProfileOut,
    ProfileTypeInfo,
    ProfileUpdate,
    RegisterRequest,
    ReportCreate,
    ReportOut,
    UserOut,
)
from src.platform.personas import (
    create_profile_persona,
    delete_profile_persona,
    generate_ai_personas,
    get_all_personas_for_profile,
    get_persona_fields,
    update_profile_persona,
)
from src.platform.profile import get_profile_types, update_profile
from src.platform.reports import (
    generate_profile_report,
    get_profile_report_by_id,
    list_profile_reports,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Platform & Multi-Tenant Layer"])


# ── Authentication Endpoints ──

@router.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user and initialize workspace profile",
)
async def register(req: RegisterRequest, response: Response):
    """Create account, provision primary profile, and issue session token."""
    try:
        user, profile, token = register_user(
            email=req.email,
            password=req.password,
            display_name=req.display_name,
        )
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=14 * 86400,
        )
        return AuthResponse(token=token, user=user, profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Registration failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="Authenticate user and issue session token",
)
async def login(req: LoginRequest, response: Response):
    """Verify credentials and issue session token."""
    try:
        user, profile, token = login_user(email=req.email, password=req.password)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=14 * 86400,
        )
        return AuthResponse(token=token, user=user, profile=profile)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except Exception as exc:
        logger.exception("Login error")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="Invalidate active session",
)
async def logout(
    response: Response,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Log out user and clear session cookie."""
    response.delete_cookie("session_token")
    return {"message": "Logged out successfully."}


@router.get(
    "/auth/me",
    summary="Get current authenticated user and profile",
)
async def get_me(auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile)):
    """Return user and profile for the authenticated session."""
    user, profile = auth
    return {"user": user, "profile": profile}


# ── Profile Endpoints ──

@router.get(
    "/profile",
    response_model=ProfileOut,
    summary="Get current user's profile",
)
async def get_my_profile(auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile)):
    """Return the authenticated user's workspace profile."""
    _, profile = auth
    return profile


@router.patch(
    "/profile",
    response_model=ProfileOut,
    summary="Update current user's profile settings & preferences",
)
async def patch_my_profile(
    update: ProfileUpdate,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Update profile fields with server-side validation."""
    _, profile = auth
    try:
        return update_profile(profile.id, update)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/profile/types",
    response_model=list[ProfileTypeInfo],
    summary="List available profile types & analytical priorities",
)
async def list_types():
    """List data-driven profile types (Scout, Researcher, Fan, Analyst, Coach, Custom)."""
    return get_profile_types()


# ── Profile Memory Endpoints ──

@router.get(
    "/profile/memory",
    response_model=list[MemoryOut],
    summary="List persistent memory entries for authenticated profile",
)
async def list_memories(
    memory_type: Optional[str] = Query(None),
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Retrieve durable memory items belonging strictly to the caller's profile."""
    _, profile = auth
    return ProfileMemoryService.get_memories(profile.id, memory_type=memory_type)


@router.post(
    "/profile/memory",
    response_model=MemoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a persistent memory item",
)
async def create_memory(
    req: MemoryCreate,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Store explicit user setting or learned analytical preference."""
    _, profile = auth
    return ProfileMemoryService.add_memory(
        profile_id=profile.id,
        memory_type=req.memory_type,
        key=req.key,
        value=req.value,
        source=req.source,
        confidence=req.confidence,
    )


@router.delete(
    "/profile/memory/{memory_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a memory item",
)
async def delete_memory(
    memory_id: str,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Remove a profile memory ensuring tenant isolation."""
    _, profile = auth
    deleted = ProfileMemoryService.delete_memory(profile.id, memory_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found or access denied.",
        )
    return {"message": "Memory deleted successfully."}


# ── Persona Endpoints ──

@router.get(
    "/profile/personas",
    response_model=list[PersonaOut],
    summary="List all accessible personas (System + Profile-owned)",
)
async def list_personas(auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile)):
    """Return protected system personas combined with the user's custom personas."""
    _, profile = auth
    return get_all_personas_for_profile(profile.id)


@router.get(
    "/profile/personas/fields",
    summary="List supported persona fields",
)
async def list_fields():
    """Return data-driven persona fields."""
    return get_persona_fields()


@router.post(
    "/profile/personas",
    response_model=PersonaOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom persona",
)
async def create_persona(
    req: PersonaCreate,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Validate and persist a custom persona under the caller's profile."""
    _, profile = auth
    try:
        return create_profile_persona(profile.id, req)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch(
    "/profile/personas/{persona_id}",
    response_model=PersonaOut,
    summary="Update a custom persona",
)
async def patch_persona(
    persona_id: str,
    req: PersonaUpdate,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Update custom persona. System personas are protected and will return 400/403."""
    _, profile = auth
    try:
        return update_profile_persona(profile.id, persona_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.delete(
    "/profile/personas/{persona_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a custom persona",
)
async def delete_persona(
    persona_id: str,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Delete custom persona. System personas are immutable."""
    _, profile = auth
    try:
        deleted = delete_profile_persona(profile.id, persona_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found or access denied.")
        return {"message": "Persona deleted successfully."}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/profile/personas/generate",
    response_model=list[PersonaOut],
    status_code=status.HTTP_201_CREATED,
    summary="Generate custom personas with AI",
)
async def generate_personas(
    req: PersonaGenerateRequest,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Generate structured and validated personas according to requested field & count."""
    _, profile = auth
    try:
        return generate_ai_personas(profile.id, req)
    except Exception as exc:
        logger.exception("AI persona generation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── Reports Endpoints ──

@router.get(
    "/reports",
    response_model=list[ReportOut],
    summary="List all reports for authenticated profile",
)
async def list_reports(auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile)):
    """List reports generated for the caller's profile."""
    _, profile = auth
    return list_profile_reports(profile.id)


@router.get(
    "/reports/{report_id}",
    response_model=ReportOut,
    summary="Get report by ID",
)
async def get_report(
    report_id: str,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Retrieve report ensuring caller ownership."""
    _, profile = auth
    report = get_profile_report_by_id(profile.id, report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found or access denied.")
    return report


@router.post(
    "/reports/generate",
    response_model=ReportOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized report from a discussion",
)
async def create_report(
    req: ReportCreate,
    auth: tuple[UserOut, ProfileOut] = Depends(get_current_user_and_profile),
):
    """Synthesize discussion findings into profile-adapted intelligence report."""
    _, profile = auth
    if not req.discussion_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="discussion_id is required.")
    try:
        return generate_profile_report(
            profile_id=profile.id,
            discussion_id=req.discussion_id,
            custom_report_type=req.report_type,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discussion not found.")
    except Exception as exc:
        logger.exception("Report generation failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
