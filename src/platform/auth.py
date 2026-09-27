"""Authentication and Session Management Service.

Provides secure cryptographic password hashing, session tokens,
and server-side profile resolution.
"""

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

from fastapi import Depends, Header, HTTPException, Request, status

from src.platform.db import get_db_cursor
from src.platform.models import ProfileOut, UserOut

logger = logging.getLogger(__name__)

ITERATIONS = 100_000
SESSION_DURATION_DAYS = 14


def hash_password(password: str) -> Tuple[str, str]:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = secrets.token_hex(16)
    pw_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    pw_hash = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt_bytes, ITERATIONS)
    return pw_hash.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify password in constant time to prevent timing attacks."""
    pw_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    computed_hash = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt_bytes, ITERATIONS).hex()
    return hmac.compare_digest(computed_hash, stored_hash)


def register_user(email: str, password: str, display_name: str) -> Tuple[UserOut, ProfileOut, str]:
    """Register a new user and initialize their primary profile atomically."""
    clean_email = email.strip().lower()
    clean_name = display_name.strip()

    if not clean_email or "@" not in clean_email:
        raise ValueError("Invalid email address format.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if len(clean_name) < 2:
        raise ValueError("Display name must be at least 2 characters.")

    user_id = f"usr-{uuid4().hex[:12]}"
    profile_id = f"prof-{uuid4().hex[:12]}"
    pw_hash, salt = hash_password(password)
    now_str = datetime.now(timezone.utc).isoformat()

    with get_db_cursor() as cur:
        # Check uniqueness
        cur.execute("SELECT id FROM users WHERE LOWER(email) = %s" if hasattr(cur, 'execute') and "%s" in "?" else "SELECT id FROM users WHERE LOWER(email) = ?", (clean_email,))
        existing = cur.fetchone()
        if existing:
            raise ValueError(f"An account with email '{clean_email}' already exists.")

        # Insert user
        cur.execute(
            """INSERT INTO users (id, email, password_hash, salt, display_name, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, clean_email, pw_hash, salt, clean_name, now_str, now_str),
        )

        # Insert default profile
        cur.execute(
            """INSERT INTO profiles (
                   id, user_id, display_name, profile_type, football_focus, experience_level,
                   preferred_analysis_style, preferred_report_type, favorite_competitions,
                   favorite_teams, favorite_analysis_areas, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id,
                user_id,
                clean_name,
                "scout",
                "Player Recruitment & Positional Profiling",
                "Professional",
                "Statistical & Quantitative",
                "Scout Report",
                '["UEFA Champions League", "FIFA World Cup", "Premier League"]',
                '["Argentina", "Manchester City", "Arsenal"]',
                '["Tactical Structures", "Pressing Metrics", "xG Differential"]',
                now_str,
                now_str,
            ),
        )

        # Create session
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)).isoformat()
        cur.execute(
            "INSERT INTO sessions (token, user_id, profile_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, user_id, profile_id, now_str, expires_at),
        )

    user = UserOut(id=user_id, email=clean_email, display_name=clean_name, created_at=now_str)
    profile = ProfileOut(
        id=profile_id,
        user_id=user_id,
        display_name=clean_name,
        profile_type="scout",
        football_focus="Player Recruitment & Positional Profiling",
        experience_level="Professional",
        preferred_analysis_style="Statistical & Quantitative",
        preferred_report_type="Scout Report",
        favorite_competitions=["UEFA Champions League", "FIFA World Cup", "Premier League"],
        favorite_teams=["Argentina", "Manchester City", "Arsenal"],
        favorite_analysis_areas=["Tactical Structures", "Pressing Metrics", "xG Differential"],
        created_at=now_str,
        updated_at=now_str,
    )
    return user, profile, token


def login_user(email: str, password: str) -> Tuple[UserOut, ProfileOut, str]:
    """Authenticate credentials and generate a secure session token."""
    clean_email = email.strip().lower()

    with get_db_cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, salt, display_name, created_at FROM users WHERE LOWER(email) = ?",
            (clean_email,),
        )
        u_row = cur.fetchone()
        if not u_row:
            raise ValueError("Invalid email or password.")

        u_dict = dict(u_row)
        if not verify_password(password, u_dict["password_hash"], u_dict["salt"]):
            raise ValueError("Invalid email or password.")

        user_id = u_dict["id"]
        # Fetch profile
        cur.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
        p_row = cur.fetchone()
        if not p_row:
            raise ValueError("Corrupted user profile state.")

        p_dict = dict(p_row)
        profile_id = p_dict["id"]

        # Generate session
        token = secrets.token_urlsafe(32)
        now_str = datetime.now(timezone.utc).isoformat()
        expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DURATION_DAYS)).isoformat()
        cur.execute(
            "INSERT INTO sessions (token, user_id, profile_id, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, user_id, profile_id, now_str, expires_at),
        )

    import json
    user = UserOut(
        id=u_dict["id"],
        email=u_dict["email"],
        display_name=u_dict["display_name"],
        created_at=str(u_dict["created_at"]),
    )
    profile = ProfileOut(
        id=p_dict["id"],
        user_id=p_dict["user_id"],
        display_name=p_dict["display_name"],
        profile_type=p_dict["profile_type"],
        football_focus=p_dict["football_focus"] or "",
        experience_level=p_dict["experience_level"] or "",
        preferred_analysis_style=p_dict["preferred_analysis_style"] or "",
        preferred_report_type=p_dict["preferred_report_type"] or "",
        favorite_competitions=json.loads(p_dict["favorite_competitions"]) if isinstance(p_dict["favorite_competitions"], str) else (p_dict["favorite_competitions"] or []),
        favorite_teams=json.loads(p_dict["favorite_teams"]) if isinstance(p_dict["favorite_teams"], str) else (p_dict["favorite_teams"] or []),
        favorite_analysis_areas=json.loads(p_dict["favorite_analysis_areas"]) if isinstance(p_dict["favorite_analysis_areas"], str) else (p_dict["favorite_analysis_areas"] or []),
        created_at=str(p_dict["created_at"]),
        updated_at=str(p_dict["updated_at"]),
    )
    return user, profile, token


def logout_user(token: str) -> None:
    """Invalidate session token."""
    if not token:
        return
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM sessions WHERE token = ?", (token.strip(),))


def get_session_profile(token: str) -> Optional[Tuple[UserOut, ProfileOut]]:
    """Resolve authenticated user and profile from session token."""
    if not token:
        return None

    import json
    now_str = datetime.now(timezone.utc).isoformat()
    with get_db_cursor() as cur:
        cur.execute(
            """SELECT s.token, s.expires_at, u.id as u_id, u.email, u.display_name as u_name, u.created_at as u_created,
                      p.id as p_id, p.display_name as p_name, p.profile_type, p.football_focus, p.experience_level,
                      p.preferred_analysis_style, p.preferred_report_type, p.favorite_competitions,
                      p.favorite_teams, p.favorite_analysis_areas, p.created_at as p_created, p.updated_at as p_updated
               FROM sessions s
               JOIN users u ON s.user_id = u.id
               JOIN profiles p ON s.profile_id = p.id
               WHERE s.token = ? AND s.expires_at > ?""",
            (token.strip(), now_str),
        )
        row = cur.fetchone()
        if not row:
            return None

        r = dict(row)
        user = UserOut(
            id=r["u_id"],
            email=r["email"],
            display_name=r["u_name"],
            created_at=str(r["u_created"]),
        )
        profile = ProfileOut(
            id=r["p_id"],
            user_id=r["u_id"],
            display_name=r["p_name"],
            profile_type=r["profile_type"],
            football_focus=r["football_focus"] or "",
            experience_level=r["experience_level"] or "",
            preferred_analysis_style=r["preferred_analysis_style"] or "",
            preferred_report_type=r["preferred_report_type"] or "",
            favorite_competitions=json.loads(r["favorite_competitions"]) if isinstance(r["favorite_competitions"], str) else (r["favorite_competitions"] or []),
            favorite_teams=json.loads(r["favorite_teams"]) if isinstance(r["favorite_teams"], str) else (r["favorite_teams"] or []),
            favorite_analysis_areas=json.loads(r["favorite_analysis_areas"]) if isinstance(r["favorite_analysis_areas"], str) else (r["favorite_analysis_areas"] or []),
            created_at=str(r["p_created"]),
            updated_at=str(r["p_updated"]),
        )
        return user, profile


async def get_current_user_and_profile(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Tuple[UserOut, ProfileOut]:
    """FastAPI dependency to extract authenticated user & profile from Authorization header or cookie."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
    elif "session_token" in request.cookies:
        token = request.cookies.get("session_token")
    elif "token" in request.query_params:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    res = get_session_profile(token)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return res
