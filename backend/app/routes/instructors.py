
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import (
    Department,
    Subject,
    Instructor,
    FeedbackSubmission,
)
from app.schemas import (
    InstructorCreate,
    InstructorUpdate,
    InstructorResponse,
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SimpleInstructor,
    SimpleSubject,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["Instructors & Subjects"],
)


# ==========================================================
# SUBJECT ENDPOINTS
# ==========================================================

def subject_response(subject: Subject) -> SubjectResponse:
    department_name = (
        subject.department.name if subject.department else None
    )

    active_instructors = [
        SimpleInstructor(id=instructor.id, name=instructor.name)
        for instructor in subject.instructors
        if instructor.is_active
    ]

    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        code=subject.code,
        department_id=subject.department_id,
        department_name=department_name,
        semester=subject.semester,
        is_active=subject.is_active,
        created_at=subject.created_at,
        instructors=active_instructors,
    )


def instructor_response(instructor: Instructor) -> InstructorResponse:
    department_name = (
        instructor.department_name
        or (
            instructor.department_rel.name
            if instructor.department_rel
            else instructor.department
        )
    )

    assigned_subjects = [
        SimpleSubject(
            id=subject.id,
            name=subject.name,
            code=subject.code,
            semester=subject.semester,
        )
        for subject in instructor.subjects
        if subject.is_active
    ]

    return InstructorResponse(
        id=instructor.id,
        name=instructor.name,
        department_id=instructor.department_id,
        department_name=department_name,
        department=department_name,
        is_active=instructor.is_active,
        created_at=instructor.created_at,
        subjects=assigned_subjects,
    )


@router.get("/subjects", response_model=List[SubjectResponse])
def get_subjects(
    department_id: Optional[int] = Query(None),
    department_name: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=8),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Return subjects with optional department and semester filters."""

    query = db.query(Subject)

    if not include_inactive:
        query = query.filter(Subject.is_active.is_(True))

    if department_id is not None:
        query = query.filter(Subject.department_id == department_id)
    elif department_name and department_name.strip():
        department = (
            db.query(Department)
            .filter(Department.name.ilike(department_name.strip()))
            .first()
        )
        if not department:
            return []
        query = query.filter(Subject.department_id == department.id)

    if semester is not None:
        query = query.filter(Subject.semester == semester)

    subjects = query.order_by(
        Subject.semester,
        Subject.name,
    ).all()

    return [subject_response(subject) for subject in subjects]


@router.post(
    "/subjects",
    response_model=SubjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_subject(
    payload: SubjectCreate,
    db: Session = Depends(get_db),
):
    """Create a subject within a department and semester."""

    clean_name = payload.name.strip()

    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subject name cannot be empty.",
        )

    department = (
        db.query(Department)
        .filter(Department.id == payload.department_id)
        .first()
    )

    if not department or not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Specified department does not exist or is inactive.",
        )

    existing = (
        db.query(Subject)
        .filter(
            Subject.department_id == department.id,
            Subject.name.ilike(clean_name),
        )
        .first()
    )

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Subject '{clean_name}' already exists in "
                    f"department '{department.name}'."
                ),
            )

        # Reactivate an existing subject instead of creating a duplicate.
        existing.is_active = True
        existing.code = (
            payload.code.strip() if payload.code else None
        )
        existing.semester = payload.semester

        if payload.instructor_ids is not None:
            instructors = (
                db.query(Instructor)
                .filter(
                    Instructor.id.in_(payload.instructor_ids),
                    Instructor.is_active.is_(True),
                )
                .all()
                if payload.instructor_ids
                else []
            )

            for instructor in instructors:
                if instructor.department_id != department.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Instructor '{instructor.name}' belongs "
                            "to another department."
                        ),
                    )

            existing.instructors = instructors

        db.commit()
        db.refresh(existing)
        return subject_response(existing)

    instructors = []
    if payload.instructor_ids:
        instructors = (
            db.query(Instructor)
            .filter(
                Instructor.id.in_(payload.instructor_ids),
                Instructor.is_active.is_(True),
            )
            .all()
        )

        for instructor in instructors:
            if instructor.department_id != department.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Instructor '{instructor.name}' belongs "
                        "to another department."
                    ),
                )

    subject = Subject(
        name=clean_name,
        code=payload.code.strip() if payload.code else None,
        department_id=department.id,
        semester=payload.semester,
        is_active=True,
        instructors=instructors,
    )

    db.add(subject)
    db.commit()
    db.refresh(subject)

    return subject_response(subject)


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    payload: SubjectUpdate,
    db: Session = Depends(get_db),
):
    """Update subject details, semester, and instructor assignments."""

    subject = (
        db.query(Subject)
        .filter(Subject.id == subject_id)
        .first()
    )

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    target_department_id = (
        payload.department_id
        if payload.department_id is not None
        else subject.department_id
    )

    if payload.department_id is not None:
        department = (
            db.query(Department)
            .filter(Department.id == payload.department_id)
            .first()
        )
        if not department or not department.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department does not exist or is inactive.",
            )

    if payload.name is not None:
        clean_name = payload.name.strip()

        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subject name cannot be empty.",
            )

        duplicate = (
            db.query(Subject)
            .filter(
                Subject.department_id == target_department_id,
                Subject.name.ilike(clean_name),
                Subject.id != subject_id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Subject '{clean_name}' already exists "
                    "in this department."
                ),
            )

        old_name = subject.name
        subject.name = clean_name

        # Keep the existing historical name update behavior.
        db.query(FeedbackSubmission).filter(
            FeedbackSubmission.subject_name == old_name,
            FeedbackSubmission.department_id == subject.department_id,
        ).update(
            {FeedbackSubmission.subject_name: clean_name},
            synchronize_session=False,
        )

    if payload.code is not None:
        subject.code = payload.code.strip() or None

    if payload.department_id is not None:
        subject.department_id = payload.department_id

    if payload.semester is not None:
        subject.semester = payload.semester

    if payload.is_active is not None:
        subject.is_active = payload.is_active

    if payload.instructor_ids is not None:
        instructors = (
            db.query(Instructor)
            .filter(
                Instructor.id.in_(payload.instructor_ids),
                Instructor.is_active.is_(True),
            )
            .all()
            if payload.instructor_ids
            else []
        )

        for instructor in instructors:
            if (
                target_department_id is not None
                and instructor.department_id != target_department_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Instructor '{instructor.name}' belongs "
                        "to another department."
                    ),
                )

        subject.instructors = instructors

    db.commit()
    db.refresh(subject)

    return subject_response(subject)


@router.delete("/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete a subject; retain historical feedback."""

    subject = (
        db.query(Subject)
        .filter(Subject.id == subject_id)
        .first()
    )

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found.",
        )

    feedback_count = (
        db.query(func.count(FeedbackSubmission.id))
        .filter(
            FeedbackSubmission.subject_name == subject.name,
            FeedbackSubmission.department_id == subject.department_id,
        )
        .scalar()
        or 0
    )

    subject.is_active = False
    db.commit()

    return {
        "message": (
            f"Subject '{subject.name}' deactivated. "
            f"{feedback_count} historical feedback records preserved."
        ),
        "subject_id": subject.id,
        "is_active": False,
    }


# ==========================================================
# INSTRUCTOR ENDPOINTS
# ==========================================================

@router.get("/instructors", response_model=List[InstructorResponse])
def get_instructors(
    department_id: Optional[int] = Query(None),
    department_name: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    subject_name: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Return instructors filtered by department or subject."""

    query = db.query(Instructor)

    if not include_inactive:
        query = query.filter(Instructor.is_active.is_(True))

    if department_id is not None:
        query = query.filter(Instructor.department_id == department_id)
    elif department_name and department_name.strip():
        department = (
            db.query(Department)
            .filter(Department.name.ilike(department_name.strip()))
            .first()
        )
        if not department:
            return []
        query = query.filter(
            Instructor.department_id == department.id
        )

    if subject_id is not None:
        query = query.join(Instructor.subjects).filter(
            Subject.id == subject_id
        )
    elif subject_name and subject_name.strip():
        query = query.join(Instructor.subjects).filter(
            Subject.name.ilike(subject_name.strip())
        )

    instructors = query.order_by(Instructor.name).all()
    return [
        instructor_response(instructor)
        for instructor in instructors
    ]


@router.post(
    "/instructors",
    response_model=InstructorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_instructor(
    payload: InstructorCreate,
    db: Session = Depends(get_db),
):
    """Create or reactivate an instructor and assign subjects."""

    clean_name = payload.name.strip()

    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instructor name cannot be empty.",
        )

    department = None

    if payload.department_id is not None:
        department = (
            db.query(Department)
            .filter(Department.id == payload.department_id)
            .first()
        )
    elif payload.department_name:
        department = (
            db.query(Department)
            .filter(
                Department.name.ilike(payload.department_name.strip())
            )
            .first()
        )

    if not department:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid department is required for the instructor.",
        )

    existing = (
        db.query(Instructor)
        .filter(Instructor.name.ilike(clean_name))
        .first()
    )

    if existing and existing.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instructor '{clean_name}' already exists.",
        )

    if existing:
        instructor = existing
        instructor.is_active = True
        instructor.department_id = department.id
        instructor.department_name = department.name
        instructor.department = department.name
    else:
        instructor = Instructor(
            name=clean_name,
            department_id=department.id,
            department_name=department.name,
            department=department.name,
            is_active=True,
        )
        db.add(instructor)

    db.flush()

    if payload.subject_ids is not None:
        subjects = (
            db.query(Subject)
            .filter(Subject.id.in_(payload.subject_ids))
            .all()
            if payload.subject_ids
            else []
        )

        for subject in subjects:
            if subject.department_id != department.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Subject '{subject.name}' belongs "
                        "to another department."
                    ),
                )

        instructor.subjects = subjects

    db.commit()
    db.refresh(instructor)

    return instructor_response(instructor)


@router.put(
    "/instructors/{instructor_id}",
    response_model=InstructorResponse,
)
def update_instructor(
    instructor_id: int,
    payload: InstructorUpdate,
    db: Session = Depends(get_db),
):
    """Update instructor details and assignments."""

    instructor = (
        db.query(Instructor)
        .filter(Instructor.id == instructor_id)
        .first()
    )

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found.",
        )

    if payload.name is not None:
        clean_name = payload.name.strip()

        if not clean_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Instructor name cannot be empty.",
            )

        duplicate = (
            db.query(Instructor)
            .filter(
                Instructor.name.ilike(clean_name),
                Instructor.id != instructor_id,
            )
            .first()
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instructor '{clean_name}' already exists.",
            )

        old_name = instructor.name
        instructor.name = clean_name

        # Preserve historical instructor-name reporting behavior.
        db.query(FeedbackSubmission).filter(
            FeedbackSubmission.instructor_name == old_name
        ).update(
            {FeedbackSubmission.instructor_name: clean_name},
            synchronize_session=False,
        )

    if payload.department_id is not None:
        department = (
            db.query(Department)
            .filter(Department.id == payload.department_id)
            .first()
        )

        if not department or not department.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Department does not exist or is inactive.",
            )

        instructor.department_id = department.id
        instructor.department_name = department.name
        instructor.department = department.name

    if payload.department_name is not None and payload.department_id is None:
        department = (
            db.query(Department)
            .filter(
                Department.name.ilike(payload.department_name.strip())
            )
            .first()
        )
        if department:
            instructor.department_id = department.id
            instructor.department_name = department.name
            instructor.department = department.name

    if payload.is_active is not None:
        instructor.is_active = payload.is_active

    if payload.subject_ids is not None:
        subjects = (
            db.query(Subject)
            .filter(Subject.id.in_(payload.subject_ids))
            .all()
            if payload.subject_ids
            else []
        )

        for subject in subjects:
            if (
                instructor.department_id is not None
                and subject.department_id != instructor.department_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Subject '{subject.name}' belongs "
                        "to another department."
                    ),
                )

        instructor.subjects = subjects

    db.commit()
    db.refresh(instructor)

    return instructor_response(instructor)


@router.delete("/instructors/{instructor_id}")
def delete_instructor(
    instructor_id: int,
    db: Session = Depends(get_db),
):
    """Soft-delete an instructor and retain historic feedback."""

    instructor = (
        db.query(Instructor)
        .filter(Instructor.id == instructor_id)
        .first()
    )

    if not instructor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instructor not found.",
        )

    feedback_count = (
        db.query(func.count(FeedbackSubmission.id))
        .filter(
            FeedbackSubmission.instructor_name == instructor.name
        )
        .scalar()
        or 0
    )

    instructor.is_active = False
    db.commit()

    return {
        "message": (
            f"Instructor '{instructor.name}' deactivated. "
            f"{feedback_count} historical feedback records preserved."
        ),
        "instructor_id": instructor.id,
        "is_active": False,
    }
