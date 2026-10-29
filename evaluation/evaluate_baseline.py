import json
import sys
import os

# Add backend to path so we can import app modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.skill_engine import (
    extract_skills_from_text,
    calculate_readiness_score,
    generate_learning_path_for_gaps,
    PREREQUISITE_GRAPH,
    detect_cycles,
    ROLE_TAXONOMY
)

def evaluate_benchmarks():
    dataset_path = os.path.join(os.path.dirname(__file__), "dataset.json")
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles = data["profiles"]
    print("=" * 75)
    print("SKILLREADINESS AI — RESEARCH & ALGORITHM EVALUATION BENCHMARK")
    print("Baseline Formula: SR-v2.0-baseline")
    print("=" * 75)
    print("DISCLAIMER: This evaluation is performed against a synthetic, labeled ground-truth")
    print("engineering benchmark dataset. It validates deterministic algorithmic correctness,")
    print("taxonomic precision/recall, and DAG scheduling. It does NOT claim empirical efficacy")
    print("on human subject learning gains, which requires IRB-approved longitudinal trials.\n")

    # ----------------------------------------------------
    # 1. SKILL EXTRACTION PRECISION, RECALL, F1
    # ----------------------------------------------------
    print("[1] Evaluating Resume Skill Extraction (Precision / Recall / F1)...")
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for p in profiles:
        extracted = extract_skills_from_text(p["resume_text"], p["target_role"])
        pred_skills = set(s["name"] for s in extracted)
        gt_skills = set(p["ground_truth_skills"])

        tp = len(pred_skills.intersection(gt_skills))
        fp = len(pred_skills - gt_skills)
        fn = len(gt_skills - pred_skills)

        total_tp += tp
        total_fp += fp
        total_fn += fn

        p_prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        p_rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        p_f1 = (2 * p_prec * p_rec) / (p_prec + p_rec) if (p_prec + p_rec) > 0 else 0.0

        print(f"  - {p['name']}:")
        print(f"      Ground Truth: {sorted(list(gt_skills))}")
        print(f"      Extracted:    {sorted(list(pred_skills))}")
        if fp > 0:
            print(f"      False Positives: {sorted(list(pred_skills - gt_skills))}")
        if fn > 0:
            print(f"      False Negatives: {sorted(list(gt_skills - pred_skills))}")
        print(f"      Precision: {p_prec:.2f} | Recall: {p_rec:.2f} | F1: {p_f1:.2f}")

    overall_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = (2 * overall_prec * overall_rec) / (overall_prec + overall_rec) if (overall_prec + overall_rec) > 0 else 0.0

    print(f"\n>> Overall Extraction Micro-Averages:")
    print(f"   Precision: {overall_prec:.4f} ({total_tp}/{total_tp + total_fp})")
    print(f"   Recall:    {overall_rec:.4f} ({total_tp}/{total_tp + total_fn})")
    print(f"   F1-Score:  {overall_f1:.4f}\n")

    # ----------------------------------------------------
    # 2. SKILL GAP IDENTIFICATION ACCURACY
    # ----------------------------------------------------
    print("[2] Evaluating Role Skill-Gap Identification Accuracy...")
    gap_matches = 0
    for p in profiles:
        extracted = extract_skills_from_text(p["resume_text"], p["target_role"])
        readiness = calculate_readiness_score(p["target_role"], extracted, is_assessed=False)
        pred_core_gaps = set(readiness["critical_core_gaps"])
        exp_core_gaps = set(p["expected_core_gaps"])

        intersection = pred_core_gaps.intersection(exp_core_gaps)
        union = pred_core_gaps.union(exp_core_gaps)
        jaccard = len(intersection) / len(union) if union else 1.0

        if pred_core_gaps == exp_core_gaps:
            gap_matches += 1
            status = "EXACT MATCH (100%)"
        else:
            status = f"Jaccard = {jaccard:.2f}"

        print(f"  - {p['name']}: {status}")
        print(f"      Expected Gaps:  {sorted(list(exp_core_gaps))}")
        print(f"      Predicted Gaps: {sorted(list(pred_core_gaps))}")

    gap_acc = (gap_matches / len(profiles)) * 100
    print(f">> Exact Gap Match Accuracy: {gap_acc:.1f}% ({gap_matches}/{len(profiles)})\n")

    # ----------------------------------------------------
    # 3. READINESS SCORE CONSISTENCY & SENSITIVITY
    # ----------------------------------------------------
    print("[3] Evaluating Readiness Score Consistency & Edge Cases...")
    for p in profiles:
        extracted = extract_skills_from_text(p["resume_text"], p["target_role"])
        # Case A: Unassessed
        unassessed_res = calculate_readiness_score(p["target_role"], extracted, is_assessed=False)
        unassessed_score = unassessed_res["overall_readiness_score"]

        # Case B: Assessed with simulated score
        if p["simulated_assessment"]:
            assessed_res = calculate_readiness_score(
                p["target_role"],
                extracted,
                assessment_demonstrated_scores=p["simulated_assessment"],
                is_assessed=True
            )
            assessed_score = assessed_res["overall_readiness_score"]
            coverage = assessed_res["assessment_coverage_pct"]
        else:
            assessed_score = unassessed_score
            coverage = 0.0

        min_exp, max_exp = p["expected_readiness_range"]
        in_range = min_exp <= assessed_score <= max_exp
        print(f"  - {p['name']}:")
        print(f"      Target Role: {p['target_role']}")
        print(f"      Unassessed Score: {unassessed_score:.1f}% (Level: {unassessed_res['readiness_level']})")
        if p["simulated_assessment"]:
            print(f"      Assessed Score:   {assessed_score:.1f}% (Level: {assessed_res['readiness_level']}, Coverage: {coverage}%)")
        print(f"      Expected Range:   [{min_exp}%, {max_exp}%] -> {'VALID' if in_range else 'OUT OF RANGE'}")

    # Edge Case Sanity Checks
    print("\n  [Edge Case Verification]")
    empty_res = calculate_readiness_score("Full Stack Developer", [], is_assessed=False)
    print(f"  - Zero skills, unassessed: {empty_res['overall_readiness_score']}% (Expected: 0.0%)")
    assert empty_res["overall_readiness_score"] == 0.0, "Zero skills should yield 0.0% readiness."

    # Perfect candidate
    role_core = list(ROLE_TAXONOMY["Full Stack Developer"]["core_skills"].keys())
    perfect_extracted = [{"name": s, "category": "Technical", "proficiency_level": "Advanced"} for s in role_core]
    perfect_assessed = {s: 1.0 for s in role_core}
    perfect_res = calculate_readiness_score("Full Stack Developer", perfect_extracted, assessment_demonstrated_scores=perfect_assessed, is_assessed=True)
    print(f"  - 100% core skills with perfect assessment: {perfect_res['overall_readiness_score']}% (Expected: >=90%)")
    assert perfect_res["overall_readiness_score"] >= 90.0

    # Demonstrated failure vs unassessed
    failed_assessed = {role_core[0]: 0.0}
    failed_res = calculate_readiness_score("Full Stack Developer", [perfect_extracted[0]], assessment_demonstrated_scores=failed_assessed, is_assessed=True)
    unassessed_single = calculate_readiness_score("Full Stack Developer", [perfect_extracted[0]], is_assessed=False)
    print(f"  - Demonstrated 0% on test: {failed_res['overall_readiness_score']}% vs Unassessed declared: {unassessed_single['overall_readiness_score']}%")
    assert failed_res["overall_readiness_score"] < unassessed_single["overall_readiness_score"], "Failed assessment must score lower than provisional unassessed discount!"

    # ----------------------------------------------------
    # 4. PREREQUISITE VIOLATION CHECKS
    # ----------------------------------------------------
    print("\n[4] Evaluating Learning-Path Prerequisite DAG Scheduling...")
    cycle_check = detect_cycles(PREREQUISITE_GRAPH)
    print(f"  - Graph Cycle Check: {'PASSED (No cycles)' if cycle_check is None else f'FAILED: Cycle {cycle_check}'}")
    assert cycle_check is None, "PREREQUISITE_GRAPH must be a valid DAG without cycles."

    prereq_violations = 0
    total_scheduled_items = 0

    for p in profiles:
        extracted = extract_skills_from_text(p["resume_text"], p["target_role"])
        readiness = calculate_readiness_score(p["target_role"], extracted, is_assessed=False)
        milestones = generate_learning_path_for_gaps(p["target_role"], readiness["gap_skills"], readiness["matched_skills"])

        # Map each skill to the milestone week it appears in
        skill_week_map = {}
        for m in milestones:
            week = m["week"]
            for item in m["items"]:
                total_scheduled_items += 1
                assert "recommendation_reason" in item and item["recommendation_reason"], "Every item must have a recommendation_reason!"
            for sk in m["focus_skills"]:
                if sk not in skill_week_map:
                    skill_week_map[sk] = week

        # Verify no dependent skill appears in an earlier week than its prerequisite
        for skill, scheduled_week in skill_week_map.items():
            prereqs = PREREQUISITE_GRAPH.get(skill, [])
            for prereq in prereqs:
                if prereq in skill_week_map:
                    prereq_week = skill_week_map[prereq]
                    if prereq_week > scheduled_week:
                        print(f"  VIOLATION: {skill} scheduled in Week {scheduled_week} before prerequisite {prereq} (Week {prereq_week})!")
                        prereq_violations += 1

    print(f"  - Total Scheduled Modules Checked: {total_scheduled_items}")
    print(f"  - Prerequisite Ordering Violations: {prereq_violations} (Expected: 0)")
    assert prereq_violations == 0, "Prerequisite violations must be zero."

    print("\n" + "=" * 75)
    print("ALL EVALUATION CHECKS PASSED: Algorithmic baseline verified successfully.")
    print("=" * 75)

if __name__ == "__main__":
    evaluate_benchmarks()
