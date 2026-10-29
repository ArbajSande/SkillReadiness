import pytest
import pytest_asyncio
import uuid
import io
import time
from httpx import AsyncClient
from app.main import app
from app.core.database import db_manager
from app.core.config import settings, Settings
from app.core.rate_limiter import reset_rate_limiter, check_rate_limit
from app.core.repository import assessments_repo, readiness_repo
from app.services.skill_engine import select_next_adaptive_question, QUESTION_BANK, ROLE_TAXONOMY

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await db_manager.connect()
    reset_rate_limiter()
    yield
    await db_manager.disconnect()

async def create_unique_user(ac: AsyncClient, prefix: str = "test") -> tuple[str, str, dict]:
    uid = f"{prefix}_{uuid.uuid4().hex[:8]}"
    email = f"{uid}@example.com"
    pwd = "SecurePassword123!"
    reg = await ac.post("/api/auth/register", json={
        "email": email,
        "full_name": f"User {uid}",
        "password": pwd
    })
    token = reg.json()["access_token"]
    user_id = reg.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers

# ---------------------------------------------------------------------------
# 1. ADAPTIVE ASSESSMENT WORKFLOW TESTS (ADAPT-v1.0-baseline)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_adaptive_assessment_lifecycle_and_difficulty_stepping():
    """
    Verify complete interactive adaptive flow:
    - Initial question starts at Intermediate.
    - Correct answer steps up difficulty to Advanced.
    - Incorrect answer steps down difficulty to Beginner.
    - Sensitive server metadata (correct_option, explanation) is never exposed before submission.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_id, token, headers = await create_unique_user(ac, "adapt_learner")

        # 1. Start adaptive session for Full Stack Developer (3 questions)
        start_resp = await ac.post("/api/assessment/adaptive/start", json={
            "target_role": "Full Stack Developer",
            "max_questions": 3
        }, headers=headers)

        assert start_resp.status_code == 200
        start_data = start_resp.json()
        asm_id = start_data["assessment_id"]
        q1 = start_data["question"]

        assert start_data["question_number"] == 1
        assert start_data["total_questions"] == 3
        assert start_data["is_completed"] is False
        assert start_data["policy_version"] == "ADAPT-v1.0-baseline"

        # Verify no correct answer leak to client
        assert "correct_option" not in q1
        assert "explanation" not in q1
        assert q1["difficulty"] == "Intermediate"

        # Lookup server question in DB to know the correct answer
        doc = await assessments_repo.find_one({"assessment_id": asm_id})
        server_q1 = doc["current_question_server"]
        correct_opt_1 = server_q1["correct_option"]

        # 2. Submit CORRECT answer for Q1 -> Expect next question at ADVANCED
        step1_resp = await ac.post("/api/assessment/adaptive/next", json={
            "assessment_id": asm_id,
            "question_id": q1["id"],
            "selected_option": correct_opt_1
        }, headers=headers)

        assert step1_resp.status_code == 200
        step1_data = step1_resp.json()
        assert step1_data["feedback"]["is_correct"] is True
        assert step1_data["feedback"]["explanation"] != ""
        assert step1_data["is_completed"] is False

        q2 = step1_data["next_question"]
        assert q2 is not None
        assert q2["id"] != q1["id"], "Repeated question served!"
        assert q2["difficulty"] == "Advanced", "Difficulty failed to step up to Advanced on correct answer!"

        # 3. Submit INCORRECT answer for Q2 -> Expect step down
        doc = await assessments_repo.find_one({"assessment_id": asm_id})
        server_q2 = doc["current_question_server"]
        wrong_opt_2 = (server_q2["correct_option"] + 1) % len(server_q2["options"])

        step2_resp = await ac.post("/api/assessment/adaptive/next", json={
            "assessment_id": asm_id,
            "question_id": q2["id"],
            "selected_option": wrong_opt_2
        }, headers=headers)

        assert step2_resp.status_code == 200
        step2_data = step2_resp.json()
        assert step2_data["feedback"]["is_correct"] is False
        assert step2_data["is_completed"] is False

        q3 = step2_data["next_question"]
        assert q3 is not None
        assert q3["id"] not in [q1["id"], q2["id"]], "Repeated question served!"
        # Advanced stepped down to Intermediate or Beginner
        assert q3["difficulty"] in ["Intermediate", "Beginner"]

        # 4. Submit answer for Q3 (final question) -> Session should complete
        doc = await assessments_repo.find_one({"assessment_id": asm_id})
        server_q3 = doc["current_question_server"]

        step3_resp = await ac.post("/api/assessment/adaptive/next", json={
            "assessment_id": asm_id,
            "question_id": q3["id"],
            "selected_option": server_q3["correct_option"]
        }, headers=headers)

        assert step3_resp.status_code == 200
        step3_data = step3_resp.json()
        assert step3_data["is_completed"] is True
        assert step3_data["next_question"] is None
        assert step3_data["result"] is not None

        result = step3_data["result"]
        assert result["total_questions"] == 3
        assert result["correct_answers"] == 2
        assert result["score_percentage"] == 66.7
        assert len(result["question_results"]) == 3
        assert len(result["demonstrated_skill_scores"]) > 0

@pytest.mark.asyncio
async def test_adaptive_tampering_and_security():
    """Verify clients cannot skip questions, submit wrong IDs, or tamper with options."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_a_id, token_a, headers_a = await create_unique_user(ac, "alice_adapt")
        user_b_id, token_b, headers_b = await create_unique_user(ac, "bob_adapt")

        # User A starts session
        start_resp = await ac.post("/api/assessment/adaptive/start", json={
            "target_role": "Backend Developer",
            "max_questions": 3
        }, headers=headers_a)
        asm_id = start_resp.json()["assessment_id"]
        q_id = start_resp.json()["question"]["id"]

        # 1. Tampering with question ID (trying to answer a different question)
        bad_q_resp = await ac.post("/api/assessment/adaptive/next", json={
            "assessment_id": asm_id,
            "question_id": "fake_question_id_999",
            "selected_option": 0
        }, headers=headers_a)
        assert bad_q_resp.status_code == 400
        assert "Question mismatch" in bad_q_resp.json()["detail"]

        # 2. Out of bounds option index
        bad_opt_resp = await ac.post("/api/assessment/adaptive/next", json={
            "assessment_id": asm_id,
            "question_id": q_id,
            "selected_option": 999
        }, headers=headers_a)
        assert bad_opt_resp.status_code == 400
        assert "valid range" in bad_opt_resp.json()["detail"].lower()

        # 3. User B tries to submit answer to User A's session -> 403 Forbidden
        hack_resp = await ac.post("/api/assessment/adaptive/next", json={
            "assessment_id": asm_id,
            "question_id": q_id,
            "selected_option": 0
        }, headers=headers_b)
        assert hack_resp.status_code == 403

@pytest.mark.asyncio
async def test_adaptive_session_continuity_and_resume():
    """Verify session can be queried and resumed via GET /api/assessment/adaptive/{id}."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_id, token, headers = await create_unique_user(ac, "resume_user")

        start = await ac.post("/api/assessment/adaptive/start", json={
            "target_role": "Full Stack Developer",
            "max_questions": 4
        }, headers=headers)
        asm_id = start.json()["assessment_id"]
        first_q = start.json()["question"]

        # Client disconnects and fetches active session
        get_resp = await ac.get(f"/api/assessment/adaptive/{asm_id}", headers=headers)
        assert get_resp.status_code == 200
        get_data = get_resp.json()
        assert get_data["assessment_id"] == asm_id
        assert get_data["question"]["id"] == first_q["id"]
        assert get_data["question_number"] == 1
        assert get_data["is_completed"] is False

# ---------------------------------------------------------------------------
# 2. READINESS HISTORY & GAP SEPARATION TESTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_readiness_history_and_gap_separation():
    """
    Verify:
    1. Historical snapshots are stored after calculations.
    2. GET /api/readiness/history returns chronological snapshots strictly for requesting user.
    3. User B cannot access User A's history.
    4. Core gaps and optional gaps are returned separately.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_a, token_a, headers_a = await create_unique_user(ac, "user_a_hist")
        user_b, token_b, headers_b = await create_unique_user(ac, "user_b_hist")

        # User A calculates readiness twice
        calc1 = await ac.post("/api/readiness/calculate", json={
            "target_role": "Backend Developer"
        }, headers=headers_a)
        assert calc1.status_code == 200
        res1 = calc1.json()
        assert "critical_core_gaps" in res1
        assert "optional_gaps" in res1

        calc2 = await ac.post("/api/readiness/calculate", json={
            "target_role": "Full Stack Developer"
        }, headers=headers_a)
        assert calc2.status_code == 200

        # Query User A's history
        hist_a = await ac.get("/api/readiness/history", headers=headers_a)
        assert hist_a.status_code == 200
        hist_data = hist_a.json()
        assert hist_data["snapshots_count"] == 2
        assert len(hist_data["snapshots"]) == 2
        assert hist_data["snapshots"][0]["target_role"] == "Backend Developer"
        assert hist_data["snapshots"][1]["target_role"] == "Full Stack Developer"
        assert len(hist_data["snapshots"][0]["critical_core_gaps"]) > 0

        # User B queries history -> must be empty (0 snapshots)
        hist_b = await ac.get("/api/readiness/history", headers=headers_b)
        assert hist_b.status_code == 200
        assert hist_b.json()["snapshots_count"] == 0

# ---------------------------------------------------------------------------
# 3. SECURITY HARDENING: RATE LIMITING & PAYLOAD BOUNDS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limiting_on_auth_endpoints():
    """Verify rapid repeated requests to auth trigger HTTP 429 Too Many Requests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Rapidly attempt login 25 times (limit is 20 per minute)
        status_codes = []
        for i in range(25):
            resp = await ac.post("/api/auth/login", json={
                "email": "rate_limit_test@example.com",
                "password": "wrong_password"
            })
            status_codes.append(resp.status_code)

        assert 429 in status_codes, f"Rate limiting failed to trigger 429! Codes received: {set(status_codes)}"
        idx_429 = status_codes.index(429)
        assert idx_429 >= 15, "Rate limiter triggered too early"

@pytest.mark.asyncio
async def test_oversized_resume_rejection():
    """Verify uploading a file exceeding 10 MB is rejected with HTTP 413 / 400."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Generate 11 MB of dummy bytes
        large_bytes = b"0" * (11 * 1024 * 1024)
        large_file = ("giant_resume.pdf", io.BytesIO(large_bytes), "application/pdf")

        resp = await ac.post("/api/resume/upload", files={"file": large_file})
        assert resp.status_code in [400, 413]
        assert "exceeds" in resp.json()["detail"].lower() or "maximum" in resp.json()["detail"].lower()

def test_production_secret_key_validation():
    """Verify setting ENV=production with weak secret key triggers security exception."""
    insecure_settings = Settings(
        ENV="production",
        SECRET_KEY="short_dev_key"
    )
    with pytest.raises(ValueError) as exc:
        insecure_settings.validate_production_security()
    assert "CRITICAL SECURITY CONFIGURATION ERROR" in str(exc.value)

    # Strong key should succeed
    strong_settings = Settings(
        ENV="production",
        SECRET_KEY="a" * 32
    )
    strong_settings.validate_production_security() # No exception raised
