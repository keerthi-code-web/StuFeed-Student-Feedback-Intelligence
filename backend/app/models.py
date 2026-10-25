
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import relationship

from app.database import Base


# Many-to-many relationship:
# One instructor can teach multiple subjects, and one subject can
# have multiple instructors.
subject_instructors = Table(
    "subject_instructors",
    Base.metadata,
    Column(
        "subject_id",
        Integer,
        ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "instructor_id",
        Integer,
        ForeignKey("instructors.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    code = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subjects = relationship(
        "Subject",
        back_populates="department",
        cascade="all, delete-orphan",
    )
    instructors = relationship(
        "Instructor",
        back_populates="department_rel",
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
        index=True,
    )
    code = Column(String(20), nullable=True)
    name = Column(String(150), nullable=False, index=True)

    # Semester in which the subject is offered, from 1 through 8.
    # The database migration sets existing subjects to semester 1.
    semester = Column(Integer, nullable=False, default=1, index=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="subjects")
    instructors = relationship(
        "Instructor",
        secondary=subject_instructors,
        back_populates="subjects",
    )


class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
        index=True,
    )
    department_name = Column(
        String(150),
        nullable=True,
        default="Computer Science and Engineering",
    )

    # Retained for backwards compatibility with existing project code.
    department = Column(String(120), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department_rel = relationship(
        "Department",
        back_populates="instructors",
    )
    subjects = relationship(
        "Subject",
        secondary=subject_instructors,
        back_populates="instructors",
    )


class StudentRecord(Base):
    __tablename__ = "student_records"

    id = Column(Integer, primary_key=True, index=True)
    register_number = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    student_name = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship(
        "FeedbackSubmission",
        back_populates="student",
    )


class FeedbackSubmission(Base):
    __tablename__ = "feedback_submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_record_id = Column(
        Integer,
        ForeignKey("student_records.id"),
        nullable=True,
    )

    department_name = Column(
        String(150),
        nullable=False,
        default="Other",
        index=True,
    )
    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
        index=True,
    )
    is_other = Column(Boolean, default=False, index=True)

    subject_name = Column(String(150), nullable=True, index=True)

    # Snapshot of the semester selected when feedback was submitted.
    # It is independent of future changes to the subject configuration.
    semester = Column(Integer, nullable=True, index=True)

    instructor_name = Column(String(120), nullable=True, index=True)
    rating = Column(Integer, nullable=False)
    feedback_text = Column(Text, nullable=False)

    sentiment_label = Column(String(20), nullable=False, index=True)
    sentiment_detail = Column(String(50), nullable=False)
    sentiment_confidence = Column(Float, nullable=False, default=0.0)
    sentiment_scores = Column(Text, nullable=True)
    is_mixed = Column(Boolean, default=False)
    clause_analysis = Column(Text, nullable=True)

    cluster_id = Column(Integer, nullable=True, index=True)
    topic_label = Column(String(150), nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

    student = relationship(
        "StudentRecord",
        back_populates="submissions",
    )
