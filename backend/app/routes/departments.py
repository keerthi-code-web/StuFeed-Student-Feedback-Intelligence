import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Department, Subject, Instructor, FeedbackSubmission, subject_instructors
from app.schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse, OtherOverview
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/departments", tags=["Departments"])

REQUIRED_DEPARTMENTS = [
    ("Artificial Intelligence and Data Science", "AIDS"),
    ("Artificial Intelligence and Machine Learning", "AIML"),
    ("Information Technology", "IT"),
    ("Computer Science and Engineering", "CSE"),
    ("Chemical Engineering", "CHEM"),
    ("Biomedical Engineering", "BME"),
]

def ensure_initial_departments(db: Session):
    """Idempotently ensures the 6 required academic departments exist without creating dummy feedback."""
    for name, code in REQUIRED_DEPARTMENTS:
        existing = db.query(Department).filter(Department.name == name).first()
        if not existing:
            dept = Department(name=name, code=code, is_active=True)
            db.add(dept)
    db.commit()

@router.get("", response_model=List[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    """Returns all active departments with counts of active subjects, instructors, and feedback."""
    ensure_initial_departments(db)
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.id).all()
    results = []

    for dept in departments:
        # Active subjects in this department
        sub_count = db.query(func.count(Subject.id)).filter(
            Subject.department_id == dept.id,
            Subject.is_active == True
        ).scalar() or 0

        # Distinct active instructors assigned to subjects in this department
        inst_count = db.query(func.count(func.distinct(subject_instructors.c.instructor_id)))\
            .join(Subject, subject_instructors.c.subject_id == Subject.id)\
            .join(Instructor, subject_instructors.c.instructor_id == Instructor.id)\
            .filter(
                Subject.department_id == dept.id,
                Subject.is_active == True,
                Instructor.is_active == True
            ).scalar() or 0

        # Feedback count for this department
        fb_count = db.query(func.count(FeedbackSubmission.id)).filter(
            FeedbackSubmission.department_name == dept.name
        ).scalar() or 0

        results.append(DepartmentResponse(
            id=dept.id,
            name=dept.name,
            code=dept.code,
            is_active=dept.is_active,
            created_at=dept.created_at,
            subject_count=sub_count,
            instructor_count=inst_count,
            feedback_count=fb_count
        ))

    return results

@router.get("/overview")
def get_departments_overview(db: Session = Depends(get_db)):
    """
    Returns overview metrics for all 6 required academic departments plus the 'Other' category.
    Strictly derived from real database records.
    """
    ensure_initial_departments(db)
    departments = db.query(Department).filter(Department.is_active == True).order_by(Department.id).all()
    
    academic_depts = []
    for dept in departments:
        sub_count = db.query(func.count(Subject.id)).filter(
            Subject.department_id == dept.id,
            Subject.is_active == True
        ).scalar() or 0

        inst_count = db.query(func.count(func.distinct(subject_instructors.c.instructor_id)))\
            .join(Subject, subject_instructors.c.subject_id == Subject.id)\
            .join(Instructor, subject_instructors.c.instructor_id == Instructor.id)\
            .filter(
                Subject.department_id == dept.id,
                Subject.is_active == True,
                Instructor.is_active == True
            ).scalar() or 0

        fb_count = db.query(func.count(FeedbackSubmission.id)).filter(
            FeedbackSubmission.department_name == dept.name
        ).scalar() or 0

        academic_depts.append({
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "subject_count": sub_count,
            "instructor_count": inst_count,
            "feedback_count": fb_count
        })

    # Overview for "Other" category (general institutional feedback)
    other_query = db.query(FeedbackSubmission).filter(
        (FeedbackSubmission.department_name == "Other") | (FeedbackSubmission.is_other == True)
    )
    other_total = other_query.count()
    other_pos = other_query.filter(FeedbackSubmission.sentiment_label == "Positive").count()
    other_neg = other_query.filter(FeedbackSubmission.sentiment_label == "Negative").count()
    other_neu = other_query.filter(FeedbackSubmission.sentiment_label == "Neutral").count()
    other_mixed = other_query.filter(FeedbackSubmission.is_mixed == True).count()

    other_overview = {
        "name": "Other",
        "description": "General Institutional Feedback",
        "total_submissions": other_total,
        "positive": other_pos,
        "negative": other_neg,
        "neutral": other_neu,
        "mixed": other_mixed
    }

    return {
        "departments": academic_depts,
        "other": other_overview
    }

@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(dept_in: DepartmentCreate, db: Session = Depends(get_db)):
    """Creates a new department while preventing blank or duplicate names."""
    clean_name = dept_in.name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department name cannot be empty."
        )

    if clean_name.lower() == "other":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'Other' is a reserved category and cannot be added as a normal department."
        )

    existing = db.query(Department).filter(Department.name.ilike(clean_name)).first()
    if existing:
        if not existing.is_active:
            # Reactivate if previously deactivated
            existing.is_active = True
            if dept_in.code:
                existing.code = dept_in.code
            db.commit()
            db.refresh(existing)
            return DepartmentResponse(
                id=existing.id,
                name=existing.name,
                code=existing.code,
                is_active=existing.is_active,
                created_at=existing.created_at,
                subject_count=0,
                instructor_count=0,
                feedback_count=0
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department '{clean_name}' already exists."
        )

    new_dept = Department(name=clean_name, code=dept_in.code, is_active=True)
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)

    return DepartmentResponse(
        id=new_dept.id,
        name=new_dept.name,
        code=new_dept.code,
        is_active=new_dept.is_active,
        created_at=new_dept.created_at,
        subject_count=0,
        instructor_count=0,
        feedback_count=0
    )

@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(dept_id: int, dept_in: DepartmentUpdate, db: Session = Depends(get_db)):
    """Updates department name or active status while protecting historical data."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    if dept_in.name is not None:
        clean_name = dept_in.name.strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department name cannot be empty.")
        if clean_name.lower() == "other":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'Other' is a reserved category.")
        
        # Check duplicate
        dup = db.query(Department).filter(
            Department.name.ilike(clean_name),
            Department.id != dept_id
        ).first()
        if dup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Department '{clean_name}' already exists.")

        # Update department name and cascade update feedback submissions department_name
        old_name = dept.name
        dept.name = clean_name
        db.query(FeedbackSubmission).filter(FeedbackSubmission.department_name == old_name).update(
            {FeedbackSubmission.department_name: clean_name}
        )

    if dept_in.code is not None:
        dept.code = dept_in.code.strip()

    if dept_in.is_active is not None:
        dept.is_active = dept_in.is_active

    db.commit()
    db.refresh(dept)

    sub_count = db.query(func.count(Subject.id)).filter(Subject.department_id == dept.id, Subject.is_active == True).scalar() or 0
    fb_count = db.query(func.count(FeedbackSubmission.id)).filter(FeedbackSubmission.department_name == dept.name).scalar() or 0

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        is_active=dept.is_active,
        created_at=dept.created_at,
        subject_count=sub_count,
        instructor_count=0,
        feedback_count=fb_count
    )

@router.delete("/{dept_id}")
def delete_department(dept_id: int, db: Session = Depends(get_db)):
    """
    Safely deactivates a department to preserve all historical feedback submissions and analytics.
    Never silently deletes or cascades destruction to historical records.
    """
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found.")

    # Check for historical feedback
    fb_count = db.query(func.count(FeedbackSubmission.id)).filter(
        FeedbackSubmission.department_name == dept.name
    ).scalar() or 0

    sub_count = db.query(func.count(Subject.id)).filter(
        Subject.department_id == dept.id
    ).scalar() or 0

    # Safe deletion
    dept.is_active = False
    # Also mark its subjects inactive
    db.query(Subject).filter(Subject.department_id == dept.id).update({Subject.is_active: False})
    db.commit()

    return {
        "message": f"Department '{dept.name}' was safely deleted. {fb_count} historical feedback records and {sub_count} subjects have been preserved.",
        "department_id": dept.id,
        "is_active": False
    }
