import pytest
import pytest_asyncio
from httpx import AsyncClient
from app.main import app
from app.core.database import db_manager

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await db_manager.connect()
    yield
    await db_manager.disconnect()

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["database"] in ["connected", "disconnected", "error"]

@pytest.mark.asyncio
async def test_auth_registration_and_login():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Register new user
        reg_payload = {
            "email": "test_engineer_2026@example.com",
            "full_name": "Test Engineer",
            "password": "SecurePassword123!"
        }
        reg_resp = await ac.post("/api/auth/register", json=reg_payload)
        # 201 if created or 400 if already exists from repeated run
        if reg_resp.status_code == 201:
            data = reg_resp.json()
            assert "access_token" in data
            assert data["user"]["email"] == reg_payload["email"]
        else:
            assert reg_resp.status_code == 400

        # Login
        login_resp = await ac.post("/api/auth/login", json={
            "email": reg_payload["email"],
            "password": reg_payload["password"]
        })
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        token = login_data["access_token"]
        assert token

        # Verify Me endpoint with token
        headers = {"Authorization": f"Bearer {token}"}
        me_resp = await ac.get("/api/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == reg_payload["email"]

@pytest.mark.asyncio
async def test_resume_upload_and_skill_extraction():
    sample_resume = """
    John Doe - Senior Software Engineer
    Experienced in building scalable microservices with Python, FastAPI, and Docker.
    Proficient in React, JavaScript, TypeScript, and MongoDB.
    Worked with Git, REST API architecture, and Redis caching.
    Strong problem solving, agile development, and team collaboration skills.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/resume/upload",
            data={"text_content": sample_resume, "target_role": "Full Stack Developer"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_skills"] > 0
        extracted_names = [s["name"] for s in data["extracted_skills"]]
        assert "Python" in extracted_names
        assert "FastAPI" in extracted_names
        assert "React" in extracted_names
        assert "MongoDB" in extracted_names

@pytest.mark.asyncio
async def test_assessment_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Generate assessment
        gen_resp = await ac.post("/api/assessment/generate", json={
            "target_role": "Full Stack Developer",
            "num_questions": 4
        })
        assert gen_resp.status_code == 200
        session = gen_resp.json()
        asm_id = session["assessment_id"]
        questions = session["questions"]
        assert len(questions) > 0

        # 2. Submit answers
        answers = {q["id"]: 0 for q in questions} # Select option 0
        submit_resp = await ac.post("/api/assessment/submit", json={
            "assessment_id": asm_id,
            "answers": answers
        })
        assert submit_resp.status_code == 200
        result = submit_resp.json()
        assert result["total_questions"] == len(questions)
        assert "score_percentage" in result
        assert len(result["question_results"]) == len(questions)

@pytest.mark.asyncio
async def test_readiness_calculation():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/api/readiness/calculate", json={
            "target_role": "Full Stack Developer"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_readiness_score" in data
        assert 0 <= data["overall_readiness_score"] <= 100
        assert data["readiness_level"] in ["Job Ready", "Near Ready", "Intermediate", "Needs Upskilling"]
        assert len(data["category_breakdown"]) > 0

@pytest.mark.asyncio
async def test_learning_path_generation_and_progress_persistence():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Generate learning path
        gen_resp = await ac.post("/api/learning-path/generate", params={"target_role": "Full Stack Developer"})
        assert gen_resp.status_code == 200
        path = gen_resp.json()
        assert len(path["milestones"]) > 0
        assert path["total_items"] > 0
        assert path["completed_items"] == 0

        # Get first item id
        first_item_id = path["milestones"][0]["items"][0]["id"]

        # 2. Update progress: mark as completed
        upd_resp = await ac.put("/api/learning-path/progress", json={
            "item_id": first_item_id,
            "completed": True
        })
        assert upd_resp.status_code == 200
        updated_path = upd_resp.json()
        assert updated_path["completed_items"] == 1
        assert updated_path["overall_progress_percentage"] > 0

        # 3. Fetch current learning path and verify persisted state
        curr_resp = await ac.get("/api/learning-path/current")
        assert curr_resp.status_code == 200
        persisted = curr_resp.json()
        assert persisted["completed_items"] == 1
        assert persisted["milestones"][0]["items"][0]["completed"] is True
