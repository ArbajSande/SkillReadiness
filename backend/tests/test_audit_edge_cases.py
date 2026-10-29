import pytest
import pytest_asyncio
import uuid
import io
from httpx import AsyncClient
from app.main import app
from app.core.database import db_manager
from app.core.repository import resumes_repo, assessments_repo, learning_paths_repo, readiness_repo
from app.services.skill_engine import (
    extract_skills_from_text,
    extract_text_from_file,
    calculate_readiness_score,
    generate_learning_path_for_gaps,
    detect_cycles,
    topological_sort_prerequisites,
    CycleDependencyError,
    ROLE_TAXONOMY,
    PREREQUISITE_GRAPH
)

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await db_manager.connect()
    yield
    await db_manager.disconnect()

# Helper to register and get auth token
async def create_test_user(ac: AsyncClient, suffix: str = None) -> tuple[str, str, dict]:
    uid = f"{suffix or 'usr'}_{uuid.uuid4().hex[:8]}"
    email = f"audit_{uid}@example.com"
    password = "AuditPassword123!"
    reg_resp = await ac.post("/api/auth/register", json={
        "email": email,
        "full_name": f"Audit User {uid}",
        "password": password
    })
    if reg_resp.status_code == 201:
        data = reg_resp.json()
        token = data["access_token"]
        user_id = data["user"]["id"]
    else:
        login_resp = await ac.post("/api/auth/login", json={
            "email": email,
            "password": password
        })
        data = login_resp.json()
        token = data["access_token"]
        user_id = data["user"]["id"]

    headers = {"Authorization": f"Bearer {token}"}
    return user_id, token, headers

# ---------------------------------------------------------------------------
# Task 2: Edge Case & Security Test Suite
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_and_corrupt_resume_upload():
    """Verify empty resumes, whitespace, and corrupt files are rejected with 400 Bad Request."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Whitespace only text
        resp1 = await ac.post("/api/resume/upload", data={"text_content": "   \n\t   "})
        assert resp1.status_code == 400
        assert "empty or contains only whitespace" in resp1.json()["detail"]

        # 2. String shorter than 10 characters
        resp2 = await ac.post("/api/resume/upload", data={"text_content": "abc"})
        assert resp2.status_code == 400
        assert "Could not extract readable text" in resp2.json()["detail"]

        # 3. Empty file (0 bytes)
        empty_file = ("empty.pdf", io.BytesIO(b""), "application/pdf")
        resp3 = await ac.post("/api/resume/upload", files={"file": empty_file})
        assert resp3.status_code == 400
        assert "empty" in resp3.json()["detail"].lower()

        # 4. Corrupt PDF bytes
        corrupt_file = ("bad.pdf", io.BytesIO(b"NOT_A_VALID_PDF_HEADER_12345"), "application/pdf")
        resp4 = await ac.post("/api/resume/upload", files={"file": corrupt_file})
        assert resp4.status_code == 400
        assert "failed" in resp4.json()["detail"].lower() or "not a valid pdf" in resp4.json()["detail"].lower()

        # 5. Unsupported file format
        unsupported = ("music.mp3", io.BytesIO(b"ID3_fake_mp3_bytes_here_long_enough"), "audio/mpeg")
        resp5 = await ac.post("/api/resume/upload", files={"file": unsupported})
        assert resp5.status_code == 400
        assert "unsupported" in resp5.json()["detail"].lower()

def test_skill_extraction_substring_and_symbol_safety():
    """Verify Java vs JavaScript, Go vs Django, and symbols like C++, C#, .NET are normalized cleanly."""
    # Java should NOT extract JavaScript
    java_text = "Senior Java developer with 5 years enterprise Spring Boot and SQL experience."
    java_skills = {s["name"] for s in extract_skills_from_text(java_text, "Backend Developer")}
    assert "Java" in java_skills
    assert "JavaScript" not in java_skills, "Java matched JavaScript via substring!"

    # JavaScript should NOT extract Java
    js_text = "Frontend engineer specialized in JavaScript, React, and CSS3."
    js_skills = {s["name"] for s in extract_skills_from_text(js_text, "Frontend Developer")}
    assert "JavaScript" in js_skills
    assert "Java" not in js_skills, "JavaScript matched Java via substring!"

    # Go language isolation (should not match Django or MongoDB)
    go_text = "Backend systems programming in Go and Docker."
    go_skills = {s["name"] for s in extract_skills_from_text(go_text, "Backend Developer")}
    assert "Go" in go_skills
    assert "Django" not in go_skills
    assert "MongoDB" not in go_skills

    # Symbols: C++ and C#
    cpp_text = "High performance systems engineer writing C++ and C# services."
    cpp_skills = {s["name"] for s in extract_skills_from_text(cpp_text, "Backend Developer")}
    assert "C++" in cpp_skills
    assert "C#" in cpp_skills

def test_negation_and_aspiration_detection():
    """Verify skills preceded by negation or aspirational phrasing are NOT extracted."""
    text = (
        "Experienced software developer. Proficient in Python and SQL. "
        "No experience with Kubernetes or Docker. "
        "Looking to learn FastAPI and GraphQL in the future. "
        "Seeking training in Redis."
    )
    extracted = {s["name"] for s in extract_skills_from_text(text, "Backend Developer")}
    assert "Python" in extracted
    assert "SQL" in extracted
    assert "Kubernetes" not in extracted, "Negated skill Kubernetes was incorrectly extracted!"
    assert "Docker" not in extracted, "Negated skill Docker was incorrectly extracted!"
    assert "FastAPI" not in extracted, "Aspirational skill FastAPI was incorrectly extracted!"
    assert "GraphQL" not in extracted, "Aspirational skill GraphQL was incorrectly extracted!"
    assert "Redis" not in extracted, "Aspirational skill Redis was incorrectly extracted!"

def test_missing_vs_demonstrated_low_proficiency():
    """
    Verify that unassessed declared skills receive a provisional 50% discount,
    whereas failing an assessment results in a demonstrated gap with 0% competency.
    Unassessed must score strictly higher than a candidate who failed the assessment.
    """
    python_skill = [{"name": "Python", "category": "Technical", "proficiency_level": "Intermediate"}]

    # Case 1: Unassessed candidate declaring Python on resume
    unassessed = calculate_readiness_score(
        target_role="Backend Developer",
        extracted_skills=python_skill,
        is_assessed=False
    )
    python_contrib_unassessed = next(sc for sc in unassessed["skill_contributions"] if sc["skill"] == "Python")
    assert python_contrib_unassessed["status"] == "declared_unassessed"
    assert python_contrib_unassessed["effective_proficiency"] == 0.35  # 0.70 * 0.50 discount
    assert unassessed["is_assessed"] is False

    # Case 2: Candidate took assessment on Python and scored 0.0 (demonstrated failure)
    failed = calculate_readiness_score(
        target_role="Backend Developer",
        extracted_skills=python_skill,
        assessment_demonstrated_scores={"Python": 0.0},
        is_assessed=True
    )
    python_contrib_failed = next(sc for sc in failed["skill_contributions"] if sc["skill"] == "Python")
    assert python_contrib_failed["status"] == "demonstrated_gap"
    assert python_contrib_failed["effective_proficiency"] == 0.0
    assert failed["is_assessed"] is True

    # Critical requirement: unassessed is not conflated with demonstrated failure
    assert unassessed["overall_readiness_score"] > failed["overall_readiness_score"], (
        "A candidate who proved 0% proficiency must score LOWER than an unassessed candidate with declared skills."
    )

@pytest.mark.asyncio
async def test_assessment_backend_grading_all_incorrect():
    """Verify that submitting incorrect answers results in 0.0% backend score and demonstrated gaps."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Generate assessment
        gen_resp = await ac.post("/api/assessment/generate", json={
            "target_role": "Backend Developer",
            "num_questions": 3
        })
        assert gen_resp.status_code == 200
        asm_data = gen_resp.json()
        asm_id = asm_data["assessment_id"]
        questions = asm_data["questions"]

        # Fetch server questions from DB to find an intentionally wrong option for each
        doc = await assessments_repo.find_one({"assessment_id": asm_id})
        server_q = doc["_server_questions"]

        wrong_answers = {}
        for q in server_q:
            correct_idx = q["correct_option"]
            wrong_idx = (correct_idx + 1) % len(q["options"])
            wrong_answers[q["id"]] = wrong_idx

        # Submit all wrong answers
        sub_resp = await ac.post("/api/assessment/submit", json={
            "assessment_id": asm_id,
            "answers": wrong_answers
        })
        assert sub_resp.status_code == 200
        result = sub_resp.json()
        assert result["correct_answers"] == 0
        assert result["score_percentage"] == 0.0
        for qr in result["question_results"]:
            assert qr["is_correct"] is False
            assert qr["selected_option"] != qr["correct_option"]

        # Demonstrated skill scores must reflect 0.0
        for skill, score in result["demonstrated_skill_scores"].items():
            assert score == 0.0

def test_readiness_score_edge_cases_and_formula():
    """Verify mathematical boundaries: empty profile = 0.0%, fully verified profile = 100.0%."""
    # 1. Empty profile
    empty_res = calculate_readiness_score("Full Stack Developer", [], is_assessed=False)
    assert empty_res["formula_version"] == "SR-v2.0-baseline"
    assert empty_res["overall_readiness_score"] == 0.0
    assert empty_res["readiness_level"] == "Needs Upskilling"
    assert len(empty_res["critical_core_gaps"]) == len(ROLE_TAXONOMY["Full Stack Developer"]["core_skills"])

    # 2. Perfect profile (100% on all core and optional skills)
    core = list(ROLE_TAXONOMY["Full Stack Developer"]["core_skills"].keys())
    opt = list(ROLE_TAXONOMY["Full Stack Developer"]["optional_skills"].keys())
    all_skills = [{"name": s, "category": "Technical", "proficiency_level": "Advanced"} for s in (core + opt)]
    all_scores = {s: 1.0 for s in (core + opt)}

    perfect_res = calculate_readiness_score(
        "Full Stack Developer",
        all_skills,
        assessment_demonstrated_scores=all_scores,
        is_assessed=True
    )
    assert perfect_res["overall_readiness_score"] == 100.0
    assert perfect_res["readiness_level"] == "Job Ready"
    assert len(perfect_res["critical_core_gaps"]) == 0
    assert len(perfect_res["gap_skills"]) == 0

def test_dependency_cycle_detection():
    """Verify cycle detection algorithm identifies cycles and raises CycleDependencyError."""
    # Normal DAG
    clean_graph = {
        "A": [],
        "B": ["A"],
        "C": ["B"]
    }
    assert detect_cycles(clean_graph) is None
    sorted_nodes = topological_sort_prerequisites(list(clean_graph.keys()), graph=clean_graph)
    assert sorted_nodes.index("A") < sorted_nodes.index("B") < sorted_nodes.index("C")

    # Cyclic graph A -> B -> C -> A
    cyclic_graph = {
        "A": ["C"],
        "B": ["A"],
        "C": ["B"]
    }
    cycle = detect_cycles(cyclic_graph)
    assert cycle is not None, "Cycle detection failed to find cycle!"
    with pytest.raises(CycleDependencyError):
        topological_sort_prerequisites(list(cyclic_graph.keys()), graph=cyclic_graph)

def test_learning_path_prerequisite_ordering():
    """Verify that prerequisites always precede dependent frameworks in the generated schedule."""
    gaps = ["Next.js", "React", "JavaScript", "HTML5", "CSS3", "Tailwind CSS"]
    milestones = generate_learning_path_for_gaps("Frontend Developer", gaps, matched_skills=[])

    skill_week_map = {}
    for m in milestones:
        for it in m["items"]:
            assert "recommendation_reason" in it and len(it["recommendation_reason"]) > 0
        for sk in m["focus_skills"]:
            if sk not in skill_week_map:
                skill_week_map[sk] = m["week"]

    # Verify: JavaScript before React
    if "JavaScript" in skill_week_map and "React" in skill_week_map:
        assert skill_week_map["JavaScript"] <= skill_week_map["React"]
    # Verify: React before Next.js
    if "React" in skill_week_map and "Next.js" in skill_week_map:
        assert skill_week_map["React"] <= skill_week_map["Next.js"]

@pytest.mark.asyncio
async def test_cross_user_security_and_authorization():
    """Verify that User A's data is strictly isolated from User B (returns 403 Forbidden)."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Create User A
        user_a_id, token_a, headers_a = await create_test_user(ac, "alice_security")
        # Create User B
        user_b_id, token_b, headers_b = await create_test_user(ac, "bob_security")

        # User A uploads a resume
        res_a = await ac.post(
            "/api/resume/upload",
            data={"text_content": "Experienced Python and SQL developer with Git."},
            headers=headers_a
        )
        assert res_a.status_code == 200
        resume_a_id = res_a.json()["id"]

        # User A creates an assessment
        asm_a = await ac.post(
            "/api/assessment/generate",
            json={"target_role": "Backend Developer", "num_questions": 3},
            headers=headers_a
        )
        assert asm_a.status_code == 200
        assessment_a_id = asm_a.json()["assessment_id"]

        # 1. User B tries to calculate readiness using User A's resume_id -> 403
        hack_calc_1 = await ac.post(
            "/api/readiness/calculate",
            json={"target_role": "Backend Developer", "resume_id": resume_a_id},
            headers=headers_b
        )
        assert hack_calc_1.status_code == 403
        assert "Access denied" in hack_calc_1.json()["detail"]

        # 2. User B tries to calculate readiness using User A's assessment_id -> 403
        hack_calc_2 = await ac.post(
            "/api/readiness/calculate",
            json={"target_role": "Backend Developer", "assessment_id": assessment_a_id},
            headers=headers_b
        )
        assert hack_calc_2.status_code == 403
        assert "Access denied" in hack_calc_2.json()["detail"]

        # 3. User B tries to submit answers to User A's assessment session -> 403
        hack_sub = await ac.post(
            "/api/assessment/submit",
            json={"assessment_id": assessment_a_id, "answers": {"any_id": 0}},
            headers=headers_b
        )
        assert hack_sub.status_code == 403

        # 4. User B tries to read User A's assessment results -> 403
        hack_get = await ac.get(f"/api/assessment/{assessment_a_id}", headers=headers_b)
        assert hack_get.status_code == 403

@pytest.mark.asyncio
async def test_module_completion_does_not_alter_assessment_competency():
    """
    Verify that marking learning modules as completed updates learning path progress,
    but does NOT inflate or alter demonstrated assessment competency in database records.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_id, token, headers = await create_test_user(ac, "competency_integrity")

        # 1. Generate and complete assessment with 1 question
        asm_gen = await ac.post(
            "/api/assessment/generate",
            json={"target_role": "Backend Developer", "num_questions": 3},
            headers=headers
        )
        asm_id = asm_gen.json()["assessment_id"]
        doc = await assessments_repo.find_one({"assessment_id": asm_id})
        sq = doc["_server_questions"]

        # Deliberately submit wrong answer to ensure 0% score
        wrong_answers = {q["id"]: (q["correct_option"] + 1) % len(q["options"]) for q in sq}
        await ac.post(
            "/api/assessment/submit",
            json={"assessment_id": asm_id, "answers": wrong_answers},
            headers=headers
        )

        # Baseline assessment state
        asm_before = await assessments_repo.find_one({"assessment_id": asm_id})
        assert asm_before["score_percentage"] == 0.0

        # 2. Generate learning path and complete learning module
        lp_gen = await ac.post("/api/learning-path/generate", params={"target_role": "Backend Developer"}, headers=headers)
        lp_data = lp_gen.json()
        item_id = lp_data["milestones"][0]["items"][0]["id"]

        upd = await ac.put(
            "/api/learning-path/progress",
            json={"item_id": item_id, "completed": True},
            headers=headers
        )
        assert upd.status_code == 200
        assert upd.json()["completed_items"] == 1

        # 3. Verify assessment competency record in DB remains completely unchanged
        asm_after = await assessments_repo.find_one({"assessment_id": asm_id})
        assert asm_after["score_percentage"] == 0.0
        assert asm_after["demonstrated_skill_scores"] == asm_before["demonstrated_skill_scores"], (
            "Learning module completion illegally altered demonstrated assessment scores!"
        )

@pytest.mark.asyncio
async def test_persistence_survives_fresh_read():
    """Verify that progress updates are persisted directly in MongoDB and readable in a fresh query."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_id, token, headers = await create_test_user(ac, "persistence_check")

        # Generate learning path
        lp_gen = await ac.post("/api/learning-path/generate", params={"target_role": "Full Stack Developer"}, headers=headers)
        lp_id = lp_gen.json()["id"]
        item_id = lp_gen.json()["milestones"][0]["items"][0]["id"]

        # Mark item completed
        await ac.put("/api/learning-path/progress", json={"item_id": item_id, "completed": True}, headers=headers)

        # Fresh direct database query bypasses HTTP cache
        fresh_doc = await learning_paths_repo.find_one({"id": lp_id})
        assert fresh_doc is not None
        assert fresh_doc["completed_items"] == 1
        assert fresh_doc["overall_progress_percentage"] > 0
        persisted_item = next(
            it for m in fresh_doc["milestones"] for it in m["items"] if it["id"] == item_id
        )
        assert persisted_item["completed"] is True
