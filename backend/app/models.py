from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Association table for Subject <-> Instructor (Many-to-Many)
subject_instructors = Table(
    "subject_instructors",
    Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id", ondelete="CASCADE"), primary_key=True),
    Column("instructor_id", Integer, ForeignKey("instructors.id", ondelete="CASCADE"), primary_key=True)
)

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    code = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subjects = relationship("Subject", back_populates="department", cascade="all, delete-orphan")
    instructors = relationship("Instructor", back_populates="department_rel")

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    code = Column(String(20), nullable=True)
    name = Column(String(150), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="subjects")
    instructors = relationship("Instructor", secondary=subject_instructors, back_populates="subjects")

class Instructor(Base):
    __tablename__ = "instructors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    department_name = Column(String(150), nullable=True, default="Computer Science and Engineering")
    department = Column(String(120), nullable=True) # Backwards-compatibility
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department_rel = relationship("Department", back_populates="instructors")
    subjects = relationship("Subject", secondary=subject_instructors, back_populates="instructors")

class StudentRecord(Base):
    __tablename__ = "student_records"

    id = Column(Integer, primary_key=True, index=True)
    register_number = Column(String(50), unique=True, nullable=False, index=True)
    student_name = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("FeedbackSubmission", back_populates="student")

class FeedbackSubmission(Base):
    __tablename__ = "feedback_submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_record_id = Column(Integer, ForeignKey("student_records.id"), nullable=True)
    
    # Department & Academic Context
    department_name = Column(String(150), nullable=False, default="Other", index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True)
    is_other = Column(Boolean, default=False, index=True)

    subject_name = Column(String(150), nullable=True, index=True)
    instructor_name = Column(String(120), nullable=True, index=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    feedback_text = Column(Text, nullable=False)
    
    # Real NLP Sentiment Analysis outputs
    sentiment_label = Column(String(20), nullable=False, index=True)  # Positive, Negative, Neutral
    sentiment_detail = Column(String(50), nullable=False)            # e.g., Positive, Negative, Neutral, Neutral (Mixed)
    sentiment_confidence = Column(Float, nullable=False, default=0.0)
    sentiment_scores = Column(Text, nullable=True)                   # JSON serialized: {"positive":..., "negative":..., "neutral":...}
    is_mixed = Column(Boolean, default=False)
    clause_analysis = Column(Text, nullable=True)                    # JSON serialized clause details

    # Real NLP Topic Intelligence outputs
    cluster_id = Column(Integer, nullable=True, index=True)
    topic_label = Column(String(150), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    student = relationship("StudentRecord", back_populates="submissions")
