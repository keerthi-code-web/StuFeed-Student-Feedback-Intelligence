
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import (
    FeedbackSubmission,
    StudentRecord,
    Department,
    Subject,
    Instructor,
)
from app.schemas import (
    FeedbackCreate,
    FeedbackSubmissionResponse,
    FeedbackAdminItem,
)
from app.nlp.pipeline import process_single_feedback


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/feedback",
    tags=["Feedback Submissions"],
)


@router.post(
    "",
    response_model=FeedbackSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
):
    """
    Validate Department -> Semester -> Subject -> Instructor.
    Run the existing NLP pipeline and save the feedback.
    """

    dept_name = payload.department_name.strip()
    is_other = dept_name.lower() == "other"

    dept_id = None
    final_dept_name = "Other" if is_other else None
    final_subject_name = None
    final_instructor_name = None
    final_semester = None

    if not is_other:
        # Validate the department.
        dept = (
            db.query(Department)
            .filter(Department.name.ilike(dept_name))
            .first()
        )

        if not dept or not dept.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Department '{dept_name}' is not recognized "
                    "or is inactive."
                ),
            )

        dept_id = dept.id
        final_dept_name = dept.name

        # Semester is required by FeedbackCreate for academic feedback.
        selected_semester = payload.semester

        if selected_semester is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Semester is required for academic feedback.",
            )

        # The subject must match the department AND semester.
        subject_name = (
            payload.subject_name.strip()
            if payload.subject_name
            else ""
        )

        subject = (
            db.query(Subject)
            .filter(
                Subject.name.ilike(subject_name),
                Subject.department_id == dept.id,
                Subject.semester == selected_semester,
            )
            .first()
        )

        if not subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Subject '{subject_name}' does not belong to "
                    f"department '{dept.name}' in semester "
                    f"{selected_semester}."
                ),
            )

        if not subject.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subject '{subject.name}' is inactive.",
            )

        final_subject_name = subject.name
        final_semester = subject.semester

        # Validate instructor existence and active status.
        instructor_name = (
            payload.instructor_name.strip()
            if payload.instructor_name
            else ""
        )

        instructor = (
            db.query(Instructor)
            .filter(Instructor.name.ilike(instructor_name))
            .first()
        )

        if not instructor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instructor '{instructor_name}' was not found.",
            )

        if not instructor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instructor '{instructor.name}' is inactive.",
            )

        # Instructor must be assigned to this subject.
        assigned_instructor_ids = [
            assigned.id for assigned in subject.instructors
        ]

        if instructor.id not in assigned_instructor_ids:
            # Preserve the existing compatibility behavior: if the
            # subject has no explicit assignments, an instructor from
            # the same department can be assigned automatically.
            if (
                not assigned_instructor_ids
                and instructor.department_id == dept.id
            ):
                subject.instructors.append(instructor)
                db.flush()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Instructor '{instructor.name}' is not assigned "
                        f"to teach '{subject.name}' in {dept.name}."
                    ),
                )

        final_instructor_name = instructor.name

    # Prevent identical re-submissions by the same student.
    duplicate_query = (
        db.query(FeedbackSubmission)
        .join(
            StudentRecord,
            FeedbackSubmission.student_record_id == StudentRecord.id,
        )
        .filter(
            StudentRecord.register_number == payload.register_number,
            FeedbackSubmission.feedback_text == payload.feedback_text,
        )
    )

    if is_other:
        duplicate_query = duplicate_query.filter(
            FeedbackSubmission.is_other.is_(True)
        )
    else:
        duplicate_query = duplicate_query.filter(
            FeedbackSubmission.department_name == final_dept_name,
            FeedbackSubmission.subject_name == final_subject_name,
            FeedbackSubmission.instructor_name == final_instructor_name,
            FeedbackSubmission.semester == final_semester,
        )

    if duplicate_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Duplicate submission detected: you have already "
                "submitted identical feedback."
            ),
        )

    # Find or create the student record.
    student = (
        db.query(StudentRecord)
        .filter(
            StudentRecord.register_number == payload.register_number
        )
        .first()
    )

    if not student:
        student = StudentRecord(
            register_number=payload.register_number,
            student_name=payload.student_name,
        )
        db.add(student)
        db.flush()
    elif student.student_name != payload.student_name:
        student.student_name = payload.student_name

    # Run the existing sentiment analysis pipeline without changing
    # its model or preprocessing implementation.
    try:
        nlp_result = process_single_feedback(payload.feedback_text)
    except Exception as exc:
        db.rollback()
        logger.exception("NLP sentiment analysis failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="NLP sentiment inference failed. Please try again.",
        ) from exc

    submission = FeedbackSubmission(
        student_record_id=student.id,
        department_name=final_dept_name,
        department_id=dept_id,
        is_other=is_other,
        subject_name=final_subject_name,
        semester=final_semester,
        instructor_name=final_instructor_name,
        rating=payload.rating,
        feedback_text=payload.feedback_text,
        sentiment_label=nlp_result["sentiment_label"],
        sentiment_detail=nlp_result["sentiment_detail"],
        sentiment_confidence=nlp_result["sentiment_confidence"],
        sentiment_scores=json.dumps(nlp_result["sentiment_scores"]),
        is_mixed=nlp_result["is_mixed"],
        clause_analysis=(
            json.dumps(nlp_result["clause_analysis"])
            if nlp_result.get("clause_analysis")
            else None
        ),
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission


@router.get("", response_model=List[FeedbackAdminItem])
def list_feedback(
    department_name: Optional[str] = Query(None),
    subject_name: Optional[str] = Query(None),
    instructor_name: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=8),
    sentiment_label: Optional[str] = Query(None),
    is_mixed: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Administrator feedback list.
    Student register numbers and names are not returned.
    """

    query = db.query(FeedbackSubmission)

    if department_name and department_name.strip():
        clean_department = department_name.strip()

        if clean_department.lower() == "other":
            query = query.filter(
                (FeedbackSubmission.department_name == "Other")
                | (FeedbackSubmission.is_other.is_(True))
            )
        else:
            query = query.filter(
                FeedbackSubmission.department_name.ilike(clean_department)
            )

    if semester is not None:
        query = query.filter(
            FeedbackSubmission.semester == semester
        )

    if subject_name and subject_name.strip():
        query = query.filter(
            FeedbackSubmission.subject_name.ilike(subject_name.strip())
        )

    if instructor_name and instructor_name.strip():
        query = query.filter(
            FeedbackSubmission.instructor_name.ilike(
                instructor_name.strip()
            )
        )

    if sentiment_label and sentiment_label.strip():
        query = query.filter(
            FeedbackSubmission.sentiment_label == sentiment_label.strip()
        )

    if is_mixed is not None:
        query = query.filter(
            FeedbackSubmission.is_mixed == is_mixed
        )

    if search and search.strip():
        query = query.filter(
            FeedbackSubmission.feedback_text.ilike(
                f"%{search.strip()}%"
            )
        )

    submissions = (
        query.order_by(desc(FeedbackSubmission.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    results = []

    for submission in submissions:
        scores = {}

        if submission.sentiment_scores:
            try:
                scores = json.loads(submission.sentiment_scores)
            except (json.JSONDecodeError, TypeError):
                scores = {}

        results.append(
            FeedbackAdminItem(
                id=submission.id,
                department_name=(
                    submission.department_name
                    or (
                        "Other"
                        if submission.is_other
                        else "Computer Science and Engineering"
                    )
                ),
                is_other=(
                    submission.is_other
                    if submission.is_other is not None
                    else False
                ),
                subject_name=(
                    submission.subject_name
                    if not submission.is_other
                    else None
                ),
                semester=submission.semester,
                instructor_name=(
                    submission.instructor_name
                    if not submission.is_other
                    else None
                ),
                rating=submission.rating,
                feedback_text=submission.feedback_text,
                sentiment_label=submission.sentiment_label,
                sentiment_detail=submission.sentiment_detail,
                sentiment_confidence=submission.sentiment_confidence,
                sentiment_scores=scores,
                is_mixed=submission.is_mixed,
                cluster_id=submission.cluster_id,
                topic_label=submission.topic_label,
                created_at=submission.created_at,
            )
        )

    return results
