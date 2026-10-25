import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Department, Subject, Instructor, FeedbackSubmission, subject_instructors
from app.schemas import (
    InstructorCreate, InstructorUpdate, InstructorResponse,
    SubjectCreate, SubjectUpdate, SubjectResponse, SimpleInstructor, SimpleSubject
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Instructors & Subjects"])

# ==========================================================
# SUBJECTS ENDPOINTS
# ==========================================================

@router.get("/subjects", response_model=List[SubjectResponse])
def get_subjects(
    department_id: Optional[int] = Query(None),
    department_name: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Returns subjects, optionally filtered by department.
    Includes assigned instructors.
    """
    query = db.query(Subject)

    if not include_inactive:
        query = query.filter(Subject.is_active == True)

    if department_id:
        query = query.filter(Subject.department_id == department_id)
    elif department_name and department_name.strip():
        dept = db.query(Department).filter(Department.name.ilike(department_name.strip())).first()
        if dept:
            query = query.filter(Subject.department_id == dept.id)
        else:
            return []

    subjects = query.order_by(Subject.name).all()
    results = []
    for s in subjects:
        dept_name = s.department.name if s.department else None
        active_insts = [
            SimpleInstructor(id=i.id, name=i.name)
            for i in s.instructors if i.is_active
        ]
        results.append(SubjectResponse(
            id=s.id,
            name=s.name,
            code=s.code,
            department_id=s.department_id,
            department_name=dept_name,
            is_active=s.is_active,
            created_at=s.created_at,
            instructors=active_insts
        ))

    return results

@router.post("/subjects", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    """Creates a new subject within a department, preventing duplicates within that department."""
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject name cannot be empty.")

    dept = db.query(Department).filter(Department.id == payload.department_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified Department does not exist.")

    # Check duplicate subject name within the same department
    existing = db.query(Subject).filter(
        Subject.department_id == payload.department_id,
        Subject.name.ilike(clean_name)
    ).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            if payload.code:
                existing.code = payload.code
            db.commit()
            db.refresh(existing)
            return SubjectResponse(
                id=existing.id,
                name=existing.name,
                code=existing.code,
                department_id=existing.department_id,
                department_name=dept.name,
                is_active=existing.is_active,
                created_at=existing.created_at,
                instructors=[]
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject '{clean_name}' already exists in department '{dept.name}'."
        )

    new_sub = Subject(
        name=clean_name,
        code=payload.code.strip() if payload.code else None,
        department_id=dept.id,
        is_active=True
    )
    db.add(new_sub)
    db.commit()
    db.refresh(new_sub)

    # Assign instructors if provided
    assigned_insts = []
    if payload.instructor_ids:
        instructors = db.query(Instructor).filter(Instructor.id.in_(payload.instructor_ids)).all()
        for inst in instructors:
            new_sub.instructors.append(inst)
            assigned_insts.append(SimpleInstructor(id=inst.id, name=inst.name))
        db.commit()

    return SubjectResponse(
        id=new_sub.id,
        name=new_sub.name,
        code=new_sub.code,
        department_id=new_sub.department_id,
        department_name=dept.name,
        is_active=new_sub.is_active,
        created_at=new_sub.created_at,
        instructors=assigned_insts
    )

@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: int, payload: SubjectUpdate, db: Session = Depends(get_db)):
    """Updates subject details and instructor assignments."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject name cannot be empty.")
        
        target_dept_id = payload.department_id if payload.department_id is not None else sub.department_id
        dup = db.query(Subject).filter(
            Subject.department_id == target_dept_id,
            Subject.name.ilike(clean_name),
            Subject.id != subject_id
        ).first()
        if dup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subject '{clean_name}' already exists in this department.")

        # Update subject name in historical feedback too
        old_name = sub.name
        sub.name = clean_name
        db.query(FeedbackSubmission).filter(FeedbackSubmission.subject_name == old_name).update(
            {FeedbackSubmission.subject_name: clean_name}
        )

    if payload.code is not None:
        sub.code = payload.code.strip() if payload.code else None

    if payload.department_id is not None:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
        if not dept:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department does not exist.")
        sub.department_id = dept.id

    if payload.is_active is not None:
        sub.is_active = payload.is_active

    if payload.instructor_ids is not None:
        sub.instructors = []
        if payload.instructor_ids:
            insts = db.query(Instructor).filter(Instructor.id.in_(payload.instructor_ids)).all()
            for inst in insts:
                sub.instructors.append(inst)

    db.commit()
    db.refresh(sub)

    dept_name = sub.department.name if sub.department else None
    active_insts = [SimpleInstructor(id=i.id, name=i.name) for i in sub.instructors if i.is_active]

    return SubjectResponse(
        id=sub.id,
        name=sub.name,
        code=sub.code,
        department_id=sub.department_id,
        department_name=dept_name,
        is_active=sub.is_active,
        created_at=sub.created_at,
        instructors=active_insts
    )

@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    """Safely deactivates a subject to preserve historical feedback."""
    sub = db.query(Subject).filter(Subject.id == subject_id).first()
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    fb_count = db.query(func.count(FeedbackSubmission.id)).filter(
        FeedbackSubmission.subject_name == sub.name
    ).scalar() or 0

    sub.is_active = False
    db.commit()

    return {
        "message": f"Subject '{sub.name}' deleted. {fb_count} historical feedback records preserved.",
        "subject_id": sub.id,
        "is_active": False
    }

# ==========================================================
# INSTRUCTORS ENDPOINTS
# ==========================================================

@router.get("/instructors", response_model=List[InstructorResponse])
def get_instructors(
    department_id: Optional[int] = Query(None),
    department_name: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    subject_name: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Returns instructors, filtered by department or subject assignment.
    """
    query = db.query(Instructor)

    if not include_inactive:
        query = query.filter(Instructor.is_active == True)

    if department_id:
        query = query.filter(Instructor.department_id == department_id)
    elif department_name and department_name.strip():
        dept = db.query(Department).filter(Department.name.ilike(department_name.strip())).first()
        if dept:
            query = query.filter(Instructor.department_id == dept.id)
        else:
            return []

    if subject_id:
        query = query.join(Instructor.subjects).filter(Subject.id == subject_id)
    elif subject_name and subject_name.strip():
        query = query.join(Instructor.subjects).filter(Subject.name.ilike(subject_name.strip()))

    instructors = query.order_by(Instructor.name).all()
    results = []

    for inst in instructors:
        dept_name = inst.department_name or (inst.department_rel.name if inst.department_rel else inst.department)
        assigned_subs = [
            SimpleSubject(id=s.id, name=s.name, code=s.code)
            for s in inst.subjects if s.is_active
        ]
        results.append(InstructorResponse(
            id=inst.id,
            name=inst.name,
            department_id=inst.department_id,
            department_name=dept_name,
            department=dept_name,
            is_active=inst.is_active,
            created_at=inst.created_at,
            subjects=assigned_subs
        ))

    return results

@router.post("/instructors", response_model=InstructorResponse, status_code=status.HTTP_201_CREATED)
def create_instructor(payload: InstructorCreate, db: Session = Depends(get_db)):
    """Creates or updates an instructor and assigns them to multiple subjects in their department."""
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor name cannot be empty.")

    # Determine department
    dept = None
    if payload.department_id:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
    elif payload.department_name:
        dept = db.query(Department).filter(Department.name.ilike(payload.department_name.strip())).first()

    if not dept:
        # Default to first department
        dept = db.query(Department).first()

    existing = db.query(Instructor).filter(Instructor.name.ilike(clean_name)).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.department_id = dept.id if dept else None
            existing.department_name = dept.name if dept else None
            existing.department = dept.name if dept else None
            db.commit()
            db.refresh(existing)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instructor '{clean_name}' already exists."
            )
        new_inst = existing
    else:
        new_inst = Instructor(
            name=clean_name,
            department_id=dept.id if dept else None,
            department_name=dept.name if dept else None,
            department=dept.name if dept else None,
            is_active=True
        )
        db.add(new_inst)
        db.commit()
        db.refresh(new_inst)

    # Assign subjects (must belong to instructor's department)
    assigned_subs = []
    if payload.subject_ids:
        subs = db.query(Subject).filter(Subject.id.in_(payload.subject_ids)).all()
        for sub in subs:
            # Prevent invalid cross-department assignment
            if dept and sub.department_id != dept.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot assign subject '{sub.name}' from a different department to instructor '{clean_name}'."
                )
            if sub not in new_inst.subjects:
                new_inst.subjects.append(sub)
            assigned_subs.append(SimpleSubject(id=sub.id, name=sub.name, code=sub.code))
        db.commit()

    return InstructorResponse(
        id=new_inst.id,
        name=new_inst.name,
        department_id=new_inst.department_id,
        department_name=dept.name if dept else None,
        department=dept.name if dept else None,
        is_active=new_inst.is_active,
        created_at=new_inst.created_at,
        subjects=assigned_subs
    )

@router.put("/instructors/{instructor_id}", response_model=InstructorResponse)
def update_instructor(instructor_id: int, payload: InstructorUpdate, db: Session = Depends(get_db)):
    """Updates instructor name, department, and subject assignments."""
    inst = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not found.")

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Instructor name cannot be empty.")
        dup = db.query(Instructor).filter(Instructor.name.ilike(clean_name), Instructor.id != instructor_id).first()
        if dup:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Instructor '{clean_name}' already exists.")

        old_name = inst.name
        inst.name = clean_name
        # Update historical feedback
        db.query(FeedbackSubmission).filter(FeedbackSubmission.instructor_name == old_name).update(
            {FeedbackSubmission.instructor_name: clean_name}
        )

    if payload.department_id is not None:
        dept = db.query(Department).filter(Department.id == payload.department_id).first()
        if dept:
            inst.department_id = dept.id
            inst.department_name = dept.name
            inst.department = dept.name

    if payload.is_active is not None:
        inst.is_active = payload.is_active

    if payload.subject_ids is not None:
        inst.subjects = []
        if payload.subject_ids:
            subs = db.query(Subject).filter(Subject.id.in_(payload.subject_ids)).all()
            for sub in subs:
                inst.subjects.append(sub)

    db.commit()
    db.refresh(inst)

    dept_name = inst.department_name or (inst.department_rel.name if inst.department_rel else inst.department)
    assigned_subs = [SimpleSubject(id=s.id, name=s.name, code=s.code) for s in inst.subjects if s.is_active]

    return InstructorResponse(
        id=inst.id,
        name=inst.name,
        department_id=inst.department_id,
        department_name=dept_name,
        department=dept_name,
        is_active=inst.is_active,
        created_at=inst.created_at,
        subjects=assigned_subs
    )

@router.delete("/instructors/{instructor_id}")
def delete_instructor(instructor_id: int, db: Session = Depends(get_db)):
    """Safely deactivates an instructor to preserve historical feedback records."""
    inst = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not inst:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instructor not found.")

    fb_count = db.query(func.count(FeedbackSubmission.id)).filter(
        FeedbackSubmission.instructor_name == inst.name
    ).scalar() or 0

    inst.is_active = False
    db.commit()

    return {
        "message": f"Instructor '{inst.name}' deleted. {fb_count} historical feedback records preserved.",
        "instructor_id": inst.id,
        "is_active": False
    }
