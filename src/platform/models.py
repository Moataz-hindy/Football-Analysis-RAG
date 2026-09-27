"""Domain models and schemas for Multi-Tenant Profile, Persona & Memory Platform."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Profile Types ──
class ProfileTypeInfo(BaseModel):
    id: str
    name: str
    tagline: str
    description: str
    priorities: list[str]
    default_report: str
    default_personas: list[str]
    tone: str


# ── Auth & Users ──
class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=2)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: str


# ── Profiles ──
class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    profile_type: Optional[str] = None
    football_focus: Optional[str] = None
    experience_level: Optional[str] = None
    preferred_analysis_style: Optional[str] = None
    preferred_report_type: Optional[str] = None
    favorite_competitions: Optional[list[str]] = None
    favorite_teams: Optional[list[str]] = None
    favorite_analysis_areas: Optional[list[str]] = None


class ProfileOut(BaseModel):
    id: str
    user_id: str
    display_name: str
    profile_type: str
    football_focus: str
    experience_level: str
    preferred_analysis_style: str
    preferred_report_type: str
    favorite_competitions: list[str]
    favorite_teams: list[str]
    favorite_analysis_areas: list[str]
    created_at: str
    updated_at: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut
    profile: ProfileOut


# ── Profile Memory ──
class MemoryCreate(BaseModel):
    memory_type: str
    key: str
    value: str
    source: str = "explicit"
    confidence: float = 1.0


class MemoryOut(BaseModel):
    id: str
    profile_id: str
    memory_type: str
    key: str
    value: str
    source: str
    confidence: float
    created_at: str
    updated_at: str


# ── Personas ──
class PersonaCreate(BaseModel):
    name: str = Field(min_length=2)
    field: str
    background: Optional[str] = None
    stance: Optional[str] = None
    communication_style: Optional[str] = None
    expertise: Optional[list[str]] = None
    priorities: Optional[list[str]] = None
    specifications: Optional[str] = None  # Freeform specification for manual creation


class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    field: Optional[str] = None
    background: Optional[str] = None
    stance: Optional[str] = None
    communication_style: Optional[str] = None
    expertise: Optional[list[str]] = None
    priorities: Optional[list[str]] = None
    is_active: Optional[bool] = None


class PersonaGenerateRequest(BaseModel):
    field: str
    count: int = Field(default=3, ge=1, le=6)
    description: Optional[str] = ""


class PersonaOut(BaseModel):
    id: str
    profile_id: Optional[str] = None
    name: str
    field: str
    background: str
    stance: str
    communication_style: str
    expertise: list[str]
    priorities: list[str]
    source: str  # 'system', 'user', or 'generated'
    is_active: bool = True
    created_at: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


# ── Reports ──
class ReportCreate(BaseModel):
    discussion_id: Optional[str] = None
    report_type: Optional[str] = None
    custom_notes: Optional[str] = None


class ReportOut(BaseModel):
    id: str
    profile_id: str
    discussion_id: Optional[str]
    report_type: str
    title: str
    content: str
    sections: list[dict[str, Any]]
    created_at: str
