import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import FeedbackSubmission, StudentRecord, Department, Subject, Instructor
from app.schemas import FeedbackCreate, FeedbackSubmissionResponse, FeedbackAdminItem
from app.nlp.pipeline import process_single_feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["Feedback Submissions"])

@router.post("", response_model=FeedbackSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackCreate, db: Session = Depends(get_db)):
    """
    Submits student feedback with rigorous server-side validation of the
    Department -> Subject -> Assigned Instructor relationship.
    Executes real RoBERTa sentiment classification and persists verified records.
    """
    dept_name = payload.department_name.strip()
    is_other = (dept_name.lower() == "other")
    dept_id = None

    if is_other:
        # Institutional feedback under 'Other' category
        final_dept_name = "Other"
        final_subject_name = None
        final_instructor_name = None
    else:
        # Academic department feedback: validate department exists and is active
        dept = db.query(Department).filter(Department.name.ilike(dept_name)).first()
        if not dept or not dept.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department '{dept_name}' is not recognized or is inactive."
            )
        dept_id = dept.id
        final_dept_name = dept.name

        # Validate subject exists, is active, and belongs to this department
        subj_name = payload.subject_name.strip() if payload.subject_name else ""
        subject = db.query(Subject).filter(
            Subject.name.ilike(subj_name),
            Subject.department_id == dept.id
        ).first()

        if not subject:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subject '{subj_name}' does not belong to department '{dept.name}'."
            )
        if not subject.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subject '{subject.name}' is currently inactive."
            )
        final_subject_name = subject.name

        # Validate instructor exists, is active, and is assigned to this subject
        inst_name = payload.instructor_name.strip() if payload.instructor_name else ""
        instructor = db.query(Instructor).filter(Instructor.name.ilike(inst_name)).first()
        if not instructor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instructor '{inst_name}' was not found in the database."
            )
        if not instructor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instructor '{instructor.name}' is currently inactive."
            )

        # Check assignment to subject
        assigned_inst_ids = [i.id for i in subject.instructors]
        if instructor.id not in assigned_inst_ids:
            # Also allow if instructor's primary department matches and subject has no explicit instructors
            if not assigned_inst_ids and instructor.department_id == dept.id:
                # Add assignment dynamically
                subject.instructors.append(instructor)
                db.commit()
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Instructor '{instructor.name}' is not assigned to teach '{subject.name}' in {dept.name}."
                )
        final_instructor_name = instructor.name

    # 1. Duplicate check (prevent identical re-submissions)
    dup_query = db.query(FeedbackSubmission).join(StudentRecord).filter(
        StudentRecord.register_number == payload.register_number,
        FeedbackSubmission.feedback_text == payload.feedback_text
    )
    if is_other:
        dup_query = dup_query.filter(FeedbackSubmission.is_other == True)
    else:
        dup_query = dup_query.filter(
            FeedbackSubmission.department_name == final_dept_name,
            FeedbackSubmission.subject_name == final_subject_name,
            FeedbackSubmission.instructor_name == final_instructor_name
        )
    
    if dup_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate submission detected: You have already submitted identical feedback."
        )

    # 2. Get or create Student Record
    student = db.query(StudentRecord).filter(StudentRecord.register_number == payload.register_number).first()
    if not student:
        student = StudentRecord(
            register_number=payload.register_number,
            student_name=payload.student_name
        )
        db.add(student)
        db.commit()
        db.refresh(student)
    else:
        if student.student_name != payload.student_name:
            student.student_name = payload.student_name
            db.commit()

    # 3. Real NLP sentiment analysis
    try:
        nlp_result = process_single_feedback(payload.feedback_text)
    except Exception as e:
        logger.error(f"NLP sentiment analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"NLP sentiment inference error: {str(e)}"
        )

    # 4. Save submission
    submission = FeedbackSubmission(
        student_record_id=student.id,
        department_name=final_dept_name,
        department_id=dept_id,
        is_other=is_other,
        subject_name=final_subject_name,
        instructor_name=final_instructor_name,
        rating=payload.rating,
        feedback_text=payload.feedback_text,
        sentiment_label=nlp_result["sentiment_label"],
        sentiment_detail=nlp_result["sentiment_detail"],
        sentiment_confidence=nlp_result["sentiment_confidence"],
        sentiment_scores=json.dumps(nlp_result["sentiment_scores"]),
        is_mixed=nlp_result["is_mixed"],
        clause_analysis=json.dumps(nlp_result["clause_analysis"]) if nlp_result["clause_analysis"] else None
    )

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return submission

@router.get("", response_model=List[FeedbackAdminItem])
def list_feedback(
    department_name: Optional[str] = Query(None, description="Filter by department name or 'Other'"),
    subject_name: Optional[str] = Query(None, description="Filter by subject name"),
    instructor_name: Optional[str] = Query(None, description="Filter by instructor name"),
    sentiment_label: Optional[str] = Query(None, description="Filter by Positive, Negative, or Neutral"),
    is_mixed: Optional[bool] = Query(None, description="Filter for mixed feedback"),
    search: Optional[str] = Query(None, description="Text search in feedback text"),
    limit: int = Query(500, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns feedback submissions for administrator review.
    PRIVACY GUARANTEE: Student register numbers and student names are completely omitted.
    """
    query = db.query(FeedbackSubmission)

    if department_name and department_name.strip():
        clean_dept = department_name.strip()
        if clean_dept.lower() == "other":
            query = query.filter(
                (FeedbackSubmission.department_name == "Other") | (FeedbackSubmission.is_other == True)
            )
        else:
            query = query.filter(FeedbackSubmission.department_name.ilike(clean_dept))

    if subject_name and subject_name.strip():
        query = query.filter(FeedbackSubmission.subject_name.ilike(subject_name.strip()))
    if instructor_name and instructor_name.strip():
        query = query.filter(FeedbackSubmission.instructor_name.ilike(instructor_name.strip()))
    if sentiment_label and sentiment_label.strip():
        query = query.filter(FeedbackSubmission.sentiment_label == sentiment_label.strip())
    if is_mixed is not None:
        query = query.filter(FeedbackSubmission.is_mixed == is_mixed)
    if search and search.strip():
        query = query.filter(FeedbackSubmission.feedback_text.ilike(f"%{search.strip()}%"))

    submissions = query.order_by(desc(FeedbackSubmission.created_at)).offset(offset).limit(limit).all()

    results = []
    for s in submissions:
        scores = {}
        if s.sentiment_scores:
            try:
                scores = json.loads(s.sentiment_scores)
            except Exception:
                scores = {}

        results.append(FeedbackAdminItem(
            id=s.id,
            department_name=s.department_name or ("Other" if s.is_other else "Computer Science and Engineering"),
            is_other=s.is_other if s.is_other is not None else False,
            subject_name=s.subject_name if not s.is_other else None,
            instructor_name=s.instructor_name if not s.is_other else None,
            rating=s.rating,
            feedback_text=s.feedback_text,
            sentiment_label=s.sentiment_label,
            sentiment_detail=s.sentiment_detail,
            sentiment_confidence=s.sentiment_confidence,
            sentiment_scores=scores,
            is_mixed=s.is_mixed,
            cluster_id=s.cluster_id,
            topic_label=s.topic_label,
            created_at=s.created_at
        ))
    return results
