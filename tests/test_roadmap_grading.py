"""
Fungsi penilaian quiz: murni, tanpa database.

Dipakai juga lewat HTTP di `test_roadmap_submission.py`. Yang di sini mengecek
logikanya langsung supaya kegagalan mudah dilacak.
"""

from src.app.modules.roadmap.service import grade_quiz, sanitize_submission_payload

QUIZ = {
    "type": "quiz",
    "passingScore": 50,
    "questions": [
        {"id": "q1", "question": "?", "options": ["a", "b"], "correctIndex": 1},
        {"id": "q2", "question": "?", "options": ["c", "d"], "correctIndex": 1},
    ],
}


def test_sanitize_removes_answer_key_from_payload():
    clean = sanitize_submission_payload(QUIZ)

    assert "correctIndex" not in clean["questions"][0]
    # `passingScore` TIDAK boleh dibuang: mahasiswa perlu tahu targetnya, dan
    # UI harus menampilkan angka yang sama dengan yang ditegakkan server.
    # Kalau ikut dibuang, frontend memakai default sendiri dan menampilkan
    # ambang yang salah.
    assert clean["passingScore"] == 50
    # Isi soal tetap harus utuh, hanya kuncinya yang dibuang.
    assert clean["questions"][0]["options"] == ["a", "b"]
    assert clean["questions"][0]["question"] == "?"


def test_sanitize_does_not_mutate_the_original():
    sanitize_submission_payload(QUIZ)
    assert "correctIndex" in QUIZ["questions"][0]
    assert "passingScore" in QUIZ


def test_sanitize_handles_snake_case_answer_key():
    clean = sanitize_submission_payload(
        {"type": "quiz", "passingScore": 50, "questions": [{"id": "q1", "correct_index": 0}]}
    )
    assert "correct_index" not in clean["questions"][0]
    assert clean["passingScore"] == 50


def test_sanitize_leaves_non_quiz_payload_untouched():
    payload = {"type": "text", "prompt": "Tempel link GitHub"}
    assert sanitize_submission_payload(payload) == payload


def test_sanitize_passes_through_non_dict():
    assert sanitize_submission_payload(None) is None
    assert sanitize_submission_payload("teks") == "teks"


def test_grade_quiz_all_correct():
    grade = grade_quiz(QUIZ, {"q1": 1, "q2": 1})
    assert grade.score == 100
    assert grade.passed is True
    assert grade.detail["correct"] == 2
    assert grade.detail["total"] == 2


def test_grade_quiz_all_wrong():
    grade = grade_quiz(QUIZ, {"q1": 0, "q2": 0})
    assert grade.score == 0
    assert grade.passed is False


def test_grade_quiz_partial_score():
    grade = grade_quiz(QUIZ, {"q1": 1, "q2": 0})
    assert grade.score == 50
    # passingScore 50, jadi 50 sudah cukup.
    assert grade.passed is True


def test_grade_quiz_missing_answers_count_as_wrong():
    """Tidak menjawab sama sekali harus dinilai 0, bukan dianggap benar."""
    grade = grade_quiz(QUIZ, {})
    assert grade.score == 0
    assert grade.passed is False


def test_grade_quiz_ignores_unknown_question_ids():
    grade = grade_quiz(QUIZ, {"q1": 1, "q2": 1, "q999": 1})
    assert grade.score == 100
    assert grade.detail["total"] == 2


def test_grade_quiz_accepts_list_shape():
    """Frontend mengirim daftar `{ questionId, selected }`."""
    grade = grade_quiz(QUIZ, [{"questionId": "q1", "selected": 1}, {"questionId": "q2", "selected": 1}])
    assert grade.score == 100


def test_grade_quiz_accepts_snake_case_list_shape():
    grade = grade_quiz(QUIZ, [{"question_id": "q1", "selected": 1}, {"question_id": "q2", "selected": 1}])
    assert grade.score == 100


def test_grade_quiz_returns_none_without_answer_key():
    """Kunci jawaban belum diatur: jangan menebak hasilnya."""
    quiz = {"type": "quiz", "questions": [{"id": "q1", "options": ["a", "b"]}]}
    assert grade_quiz(quiz, {"q1": 0}) is None


def test_grade_quiz_returns_none_for_non_quiz():
    assert grade_quiz({"type": "text", "prompt": "x"}, {"q1": 0}) is None


def test_grade_quiz_respects_strict_passing_score():
    quiz = {
        "passingScore": 100,
        "questions": [
            {"id": "q1", "correctIndex": 1},
            {"id": "q2", "correctIndex": 1},
        ],
    }
    assert grade_quiz(quiz, {"q1": 1, "q2": 0}).score == 50
    assert grade_quiz(quiz, {"q1": 1, "q2": 0}).passed is False
    assert grade_quiz(quiz, {"q1": 1, "q2": 1}).passed is True
