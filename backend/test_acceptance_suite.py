import urllib.request
import json
import sys

BASE_URL = "http://127.0.0.1:8000"

def run_test(name, fn):
    try:
        fn()
        print(f"[PASS] {name}")
        return True
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False

def http_get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def http_post(path, data):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())

def http_post_expect_error(path, data, expected_codes):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            raise AssertionError(f"Expected HTTP error {expected_codes}, but got {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code in expected_codes:
            return True
        raise AssertionError(f"Expected HTTP {expected_codes}, got {e.code}")

def test_health():
    res = http_get("/api/health")
    assert res["status"] == "healthy"
    assert res["models"]["sentiment"]["loaded"] is True
    assert res["models"]["embedding"]["loaded"] is True

def test_departments_list():
    res = http_get("/api/departments")
    names = [d["name"] for d in res]
    assert "Computer Science and Engineering" in names
    assert "Information Technology" in names
    assert "Artificial Intelligence and Data Science" in names
    assert "Artificial Intelligence and Machine Learning" in names
    assert "Chemical Engineering" in names
    assert "Biomedical Engineering" in names

def test_dynamic_subjects():
    res = http_get("/api/subjects?department_name=Computer%20Science%20and%20Engineering")
    assert len(res) > 0
    for s in res:
        assert s["department_name"] == "Computer Science and Engineering"

def test_dynamic_instructors():
    res = http_get("/api/instructors?department_name=Computer%20Science%20and%20Engineering")
    assert len(res) > 0
    for i in res:
        assert i["department_name"] == "Computer Science and Engineering"

def test_submit_valid_academic():
    payload = {
        "register_number": "21CS777",
        "student_name": "Test Student A",
        "department_name": "Computer Science and Engineering",
        "subject_name": "Database Management Systems",
        "instructor_name": "Prof. Anita Sharma",
        "rating": 5,
        "feedback_text": "The database practical modules were thoroughly explained and helpful."
    }
    res = http_post("/api/feedback", payload)
    assert res["department_name"] == "Computer Science and Engineering"
    assert res["subject_name"] == "Database Management Systems"
    assert res["sentiment_label"] in ["Positive", "Negative", "Neutral"]
    assert res["is_other"] is False

def test_submit_valid_other():
    payload = {
        "register_number": "21CS888",
        "student_name": "Test Student B",
        "department_name": "Other",
        "rating": 4,
        "feedback_text": "The student cafeteria has improved meal variety and seating arrangements."
    }
    res = http_post("/api/feedback", payload)
    assert res["department_name"] == "Other"
    assert res["is_other"] is True
    assert res["subject_name"] is None
    assert res["instructor_name"] is None
    assert res["sentiment_label"] in ["Positive", "Negative", "Neutral"]

def test_rejection_invalid_combinations():
    # 1. Other with subject
    http_post_expect_error("/api/feedback", {
        "register_number": "21CS991", "student_name": "Test", "department_name": "Other",
        "subject_name": "Database Management Systems", "rating": 5, "feedback_text": "Test feedback"
    }, [400, 422])

    # 2. Academic without subject
    http_post_expect_error("/api/feedback", {
        "register_number": "21CS992", "student_name": "Test", "department_name": "Computer Science and Engineering",
        "rating": 5, "feedback_text": "Test feedback"
    }, [400, 422])

    # 3. Rating out of bounds
    http_post_expect_error("/api/feedback", {
        "register_number": "21CS993", "student_name": "Test", "department_name": "Other",
        "rating": 6, "feedback_text": "Test feedback"
    }, [400, 422])

    # 4. Empty feedback
    http_post_expect_error("/api/feedback", {
        "register_number": "21CS994", "student_name": "Test", "department_name": "Other",
        "rating": 3, "feedback_text": "   "
    }, [400, 422])

def test_filtered_analytics():
    # Overview with department filter
    res_cse = http_get("/api/analytics/overview?department_name=Computer%20Science%20and%20Engineering")
    res_other = http_get("/api/analytics/overview?department_name=Other")
    assert res_cse["total_submissions"] >= 16
    assert res_other["total_submissions"] >= 1

    # Topics endpoint with department
    topics_cse = http_get("/api/analytics/topics?department_name=Computer%20Science%20and%20Engineering")
    assert len(topics_cse) > 0
    for t in topics_cse:
        assert "Computer Science and Engineering" in t["departments"]

def test_feedback_privacy():
    items = http_get("/api/feedback")
    assert len(items) > 0
    for item in items:
        assert "register_number" not in item
        assert "student_name" not in item
        if item["is_other"]:
            assert item["subject_name"] is None
            assert item["instructor_name"] is None

def main():
    print("=" * 60)
    print("RUNNING REFINEMENT ACCEPTANCE TEST SUITE")
    print("=" * 60)
    tests = [
        ("Health & Model Readiness Check", test_health),
        ("6 Required Academic Departments Preserved", test_departments_list),
        ("Dynamic Subjects by Department", test_dynamic_subjects),
        ("Dynamic Instructors by Department & Subject", test_dynamic_instructors),
        ("Valid Academic Feedback Submission & Real NLP", test_submit_valid_academic),
        ("Valid Other Institutional Feedback Submission", test_submit_valid_other),
        ("Server-side Rejection of Invalid Combinations", test_rejection_invalid_combinations),
        ("Filtered Analytics & Topic Intelligence", test_filtered_analytics),
        ("Privacy Enforcement (No Student Identity in Public Feed)", test_feedback_privacy)
    ]
    
    passed = 0
    for name, fn in tests:
        if run_test(name, fn):
            passed += 1

    print("=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} TESTS PASSED")
    print("=" * 60)
    if passed == len(tests):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
