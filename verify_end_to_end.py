import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def post(endpoint, data, token=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {})
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def put(endpoint, data, token=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {})
        },
        method="PUT"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def get(endpoint, token=None):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"} if token else {},
        method="GET"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def post_form(endpoint, form_fields, token=None):
    url = f"{BASE_URL}{endpoint}"
    data = urllib.parse.urlencode(form_fields).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            **({"Authorization": f"Bearer {token}"} if token else {})
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def run_e2e_verification():
    print("=" * 70)
    print("SKILLREADINESS AI - END-TO-END VERIFICATION RUN (WITH ADAPTIVE FLOW)")
    print("=" * 70)

    timestamp = int(time.time())
    email = f"adaptive_tester_{timestamp}@skillreadiness.ai"
    password = "SecurePassword2026!"
    name = "Adaptive Flow Tester"

    # 1. Registration
    print("\n[Step 1] User Registration...")
    status, reg_res = post("/api/auth/register", {"email": email, "full_name": name, "password": password})
    assert status == 201, f"Expected 201, got {status}"
    token = reg_res["access_token"]
    user_id = reg_res["user"]["id"]
    print(f" PASS: Registered user id='{user_id}', email='{email}'")

    # 2. Login
    print("\n[Step 2] User Login...")
    status, login_res = post("/api/auth/login", {"email": email, "password": password})
    assert status == 200, f"Expected 200, got {status}"
    login_token = login_res["access_token"]
    assert login_token
    print(f" PASS: Logged in successfully, token received.")

    # 3. Resume Upload & Skill Extraction
    print("\n[Step 3 & 4] Resume Upload & Skill Extraction...")
    resume_text = (
        "Software Engineer with 4 years building scalable services using Python, FastAPI, and Docker. "
        "Experienced in frontend development with React, TypeScript, and Tailwind CSS. "
        "Worked with MongoDB, PostgreSQL, and Redis. Proficient in Git, REST API design, and Agile teamwork."
    )
    status, resume_res = post_form(
        "/api/resume/upload",
        {"text_content": resume_text, "target_role": "Full Stack Developer"},
        token=login_token
    )
    assert status == 200, f"Expected 200, got {status}"
    resume_id = resume_res["id"]
    skills = resume_res["extracted_skills"]
    assert len(skills) > 0, "No skills extracted"
    extracted_names = [s["name"] for s in skills]
    print(f" PASS: Resume uploaded (id={resume_id}). Extracted {len(skills)} skills: {', '.join(extracted_names[:7])}...")

    # 5. Interactive Adaptive Assessment (ADAPT-v1.0-baseline)
    print("\n[Step 5] Interactive Adaptive Assessment (ADAPT-v1.0-baseline)...")
    status, start_res = post("/api/assessment/adaptive/start", {
        "target_role": "Full Stack Developer",
        "max_questions": 4
    }, token=login_token)
    assert status == 200
    asm_id = start_res["assessment_id"]
    assert start_res["question_number"] == 1
    assert "correct_option" not in start_res["question"], "SECURITY BREACH: correct_option leaked to client!"
    print(f" PASS: Started adaptive assessment '{asm_id}'. Question 1 difficulty: {start_res['question']['difficulty']}")

    current_q = start_res["question"]
    is_done = False
    question_count = 0

    while not is_done and current_q:
        question_count += 1
        q_id = current_q["id"]
        # Intentionally choose an answer (e.g. option 0)
        selected_opt = 0
        status, step_res = post("/api/assessment/adaptive/next", {
            "assessment_id": asm_id,
            "question_id": q_id,
            "selected_option": selected_opt
        }, token=login_token)
        assert status == 200
        fb = step_res["feedback"]
        print(f"       Q{question_count} [{current_q['skill']} - {current_q['difficulty']}]: Answered {selected_opt} -> Correct: {fb['is_correct']}. Feedback: {fb['explanation'][:60]}...")
        
        is_done = step_res["is_completed"]
        if is_done:
            result = step_res["result"]
            score_pct = result["score_percentage"]
            print(f" PASS: Adaptive assessment completed! Final Score: {score_pct}% ({result['correct_answers']}/{result['total_questions']})")
            break
        current_q = step_res["next_question"]
        assert "correct_option" not in current_q, "SECURITY BREACH: Next question leaked answer!"

    # 6. Readiness Calculation with Core vs Optional Gap Separation
    print("\n[Step 6] Readiness Calculation (SR-v2.0-baseline)...")
    status, readiness_res = post("/api/readiness/calculate", {
        "target_role": "Full Stack Developer",
        "resume_id": resume_id,
        "assessment_id": asm_id
    }, token=login_token)
    assert status == 200
    readiness_id = readiness_res["id"]
    readiness_score = readiness_res["overall_readiness_score"]
    level = readiness_res["readiness_level"]
    critical_gaps = readiness_res.get("critical_core_gaps", [])
    optional_gaps = readiness_res.get("optional_gaps", [])
    print(f" PASS: Readiness computed! Score: {readiness_score}%, Level: '{level}'")
    print(f"       Critical Core Gaps ({len(critical_gaps)}): {critical_gaps}")
    print(f"       Optional Elective Gaps ({len(optional_gaps)}): {optional_gaps}")

    # 6b. Readiness History Snapshots
    print("\n[Step 6b] Readiness History Snapshots...")
    status, history_res = get("/api/readiness/history", token=login_token)
    assert status == 200
    snapshots = history_res["snapshots"]
    assert len(snapshots) >= 1
    latest_snap = snapshots[-1]
    assert latest_snap["target_role"] == "Full Stack Developer"
    assert latest_snap["overall_readiness_score"] == readiness_score
    print(f" PASS: Retrieved {len(snapshots)} readiness snapshot(s). Latest score: {latest_snap['overall_readiness_score']}% recorded at {latest_snap['created_at']}.")

    # 7. Prerequisite-Aware Learning-Path Generation
    print("\n[Step 7] Prerequisite-Aware Learning-Path Generation...")
    url_target = urllib.parse.quote("Full Stack Developer")
    status, lp_res = post(f"/api/learning-path/generate?target_role={url_target}", {}, token=login_token)
    assert status == 200
    lp_id = lp_res["id"]
    milestones = lp_res["milestones"]
    total_items = lp_res["total_items"]
    print(f" PASS: Learning path generated! ID='{lp_id}', Total Milestones: {len(milestones)}, Total Modules: {total_items}")

    # 8. Progress Persistence and Competency Decoupling Verification
    print("\n[Step 8] Progress Persistence & Assessment Competency Decoupling...")
    first_item_id = milestones[0]["items"][0]["id"]
    status, prog_res = put("/api/learning-path/progress", {
        "item_id": first_item_id,
        "completed": True
    }, token=login_token)
    assert status == 200
    assert prog_res["completed_items"] == 1
    assert prog_res["overall_progress_percentage"] > 0
    print(f" PASS: Marked module '{first_item_id}' completed. Progress is now {prog_res['overall_progress_percentage']}%.")

    # Verify persistence by fetching fresh state from DB
    status, fetch_res = get("/api/learning-path/current", token=login_token)
    assert status == 200
    assert fetch_res["completed_items"] == 1
    assert fetch_res["milestones"][0]["items"][0]["completed"] is True
    print(f" PASS: Verified persistence via fresh GET /api/learning-path/current from MongoDB!")

    # Verify learning module completion did NOT alter demonstrated assessment competency
    status, resume_check = get("/api/resume/latest", token=login_token)
    assert status == 200
    # Assessment record must remain authentic
    status, asm_check = get(f"/api/assessment/{asm_id}", token=login_token)
    assert status == 200
    assert asm_check["score_percentage"] == score_pct
    print(f" PASS: Demonstrated assessment competency strictly preserved ({asm_check['score_percentage']}%); learning module progress decoupled from test scores.")

    print("\n" + "=" * 70)
    print("ALL 9 COMPREHENSIVE END-TO-END FLOWS VERIFIED WITH REAL API & MONGODB!")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_verification()
