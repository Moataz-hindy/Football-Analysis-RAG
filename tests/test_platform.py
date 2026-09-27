"""Unit and integration tests for Multi-Tenant Auth, Profile, Personas & Memory."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.platform.db import init_db
# from src.discussion.graph import build_discussion_graph
from src.discussion.graph import build_discussion_graph


@pytest.fixture(scope="module", autouse=True)
def setup_platform():
    init_db()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_auth_registration_and_login(client: TestClient):
    from uuid import uuid4
    email = f"scout_{uuid4().hex[:8]}@football.ai"
    reg_payload = {
        "email": email,
        "password": "securepassword123",
        "display_name": "Marwan Scout",
    }
    # 1. Register
    reg_resp = client.post("/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "token" in reg_data
    token = reg_data["token"]
    assert reg_data["user"]["email"] == email
    assert reg_data["profile"]["profile_type"] == "scout"

    # 2. Get Me
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["display_name"] == "Marwan Scout"

    # 3. Login
    login_resp = client.post("/auth/login", json={"email": email, "password": "securepassword123"})
    assert login_resp.status_code == 200
    assert "token" in login_resp.json()


def test_profile_update_and_types(client: TestClient):
    from uuid import uuid4
    reg = client.post(
        "/auth/register",
        json={"email": f"analyst_{uuid4().hex[:8]}@football.ai", "password": "password123", "display_name": "Tactical Analyst"},
    ).json()
    token = reg["token"]

    # 1. List types
    types_resp = client.get("/profile/types")
    assert types_resp.status_code == 200
    types = types_resp.json()
    assert any(t["id"] == "scout" for t in types)
    assert any(t["id"] == "researcher" for t in types)

    # 2. Update Profile
    update_payload = {
        "profile_type": "researcher",
        "football_focus": "Tactical Compactness & Counter-Pressing",
        "favorite_teams": ["Arsenal", "Real Madrid"],
    }
    patch_resp = client.patch(
        "/profile",
        json=update_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_resp.status_code == 200
    updated = patch_resp.json()
    assert updated["profile_type"] == "researcher"
    assert updated["football_focus"] == "Tactical Compactness & Counter-Pressing"
    assert "Arsenal" in updated["favorite_teams"]


def test_profile_memory_isolation(client: TestClient):
    from uuid import uuid4
    user_a = client.post("/auth/register", json={"email": f"user_a_{uuid4().hex[:8]}@football.ai", "password": "passwordA123", "display_name": "User A"}).json()
    token_a = user_a["token"]

    user_b = client.post("/auth/register", json={"email": f"user_b_{uuid4().hex[:8]}@football.ai", "password": "passwordB123", "display_name": "User B"}).json()
    token_b = user_b["token"]

    # User A creates memory
    mem_resp = client.post(
        "/profile/memory",
        json={"memory_type": "preference", "key": "Preferred Detail", "value": "Extremely High Statistical Validation", "source": "explicit"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert mem_resp.status_code == 201
    mem_id = mem_resp.json()["id"]

    # User A sees it
    mems_a = client.get("/profile/memory", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert any(m["id"] == mem_id for m in mems_a)

    # User B CANNOT see User A's memory (Tenant Isolation)
    mems_b = client.get("/profile/memory", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert not any(m["id"] == mem_id for m in mems_b)

    # User B CANNOT delete User A's memory
    del_resp = client.delete(f"/profile/memory/{mem_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_resp.status_code == 404


def test_persona_management_and_protection(client: TestClient):
    from uuid import uuid4
    user = client.post("/auth/register", json={"email": f"persona_{uuid4().hex[:8]}@football.ai", "password": "password123", "display_name": "Persona Tester"}).json()
    token = user["token"]
    # 1. System personas are listed and protected
    personas = client.get("/profile/personas", headers={"Authorization": f"Bearer {token}"}).json()
    assert any(p["source"] == "system" for p in personas)

    # Cannot delete system persona
    del_sys = client.delete("/profile/personas/tactical_analyst", headers={"Authorization": f"Bearer {token}"})
    assert del_sys.status_code == 400

    # 2. Create custom persona
    custom_req = {
        "name": "Youth Recruitment Specialist",
        "field": "Scouting & Recruitment",
        "specifications": "Identify U21 players with high physical acceleration, pressing intensity, and tactical adaptability.",
    }
    create_resp = client.post("/profile/personas", json=custom_req, headers={"Authorization": f"Bearer {token}"})
    assert create_resp.status_code == 201
    custom_p = create_resp.json()
    assert custom_p["name"] == "Youth Recruitment Specialist"
    assert custom_p["source"] == "user"

    # 3. AI Persona Generation
    ai_gen_resp = client.post(
        "/profile/personas/generate",
        json={"field": "Tactical Analysis", "count": 2, "description": "High block pressing specialists"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ai_gen_resp.status_code == 201
    ai_personas = ai_gen_resp.json()
    assert len(ai_personas) == 2
    assert all(p["source"] == "generated" for p in ai_personas)


def test_dynamic_graph_strongly_connected():
    for count in [2, 3, 4, 5, 6, 8]:
        agents = [f"agent_{i}" for i in range(count)]
        g = build_discussion_graph(agents)
        assert g.is_strongly_connected()


def test_personalized_reports_and_isolation(client: TestClient):
    from scripts.test_manual import main as make_demo
    make_demo()

    from uuid import uuid4
    user_a = client.post("/auth/register", json={"email": f"rep_a_{uuid4().hex[:8]}@football.ai", "password": "password123", "display_name": "Report User A"}).json()
    token_a = user_a["token"]

    user_b = client.post("/auth/register", json={"email": f"rep_b_{uuid4().hex[:8]}@football.ai", "password": "password123", "display_name": "Report User B"}).json()
    token_b = user_b["token"]
    # Generate report for User A
    gen_resp = client.post(
        "/reports/generate",
        json={"discussion_id": "manual-demo-001", "report_type": "Scout Report"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert gen_resp.status_code == 201
    rep = gen_resp.json()
    assert rep["report_type"] == "Scout Report"
    assert len(rep["sections"]) > 0
    rep_id = rep["id"]

    # User A can retrieve it
    get_resp = client.get(f"/reports/{rep_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_resp.status_code == 200

    # User B CANNOT retrieve User A's report (Tenant isolation)
    get_b = client.get(f"/reports/{rep_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b.status_code == 404
