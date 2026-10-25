
from datetime import datetime
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ==========================================================
# DEPARTMENT SCHEMAS
# ==========================================================

class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Department name cannot be empty.")
        return value


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    id: int
    is_active: bool
    created_at: datetime
    subject_count: int = 0
    instructor_count: int = 0
    feedback_count: int = 0

    class Config:
        from_attributes = True


class OtherOverview(BaseModel):
    total_submissions: int = 0
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    mixed: int = 0


# ==========================================================
# SUBJECT SCHEMAS
# ==========================================================

class SubjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)
    department_id: int
    semester: int = Field(
        ...,
        ge=1,
        le=8,
        description="Semester number from 1 to 8",
    )

    @field_validator("name")
    @classmethod
    def validate_subject_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Subject name cannot be empty.")
        return value


class SubjectCreate(SubjectBase):
    instructor_ids: Optional[List[int]] = []


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)
    department_id: Optional[int] = None
    semester: Optional[int] = Field(None, ge=1, le=8)
    is_active: Optional[bool] = None
    instructor_ids: Optional[List[int]] = None


class SimpleInstructor(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class SubjectResponse(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    semester: int = 1
    is_active: bool
    created_at: datetime
    instructors: List[SimpleInstructor] = []

    class Config:
        from_attributes = True


# ==========================================================
# INSTRUCTOR SCHEMAS
# ==========================================================

class InstructorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    department_id: Optional[int] = None
    department_name: Optional[str] = "Computer Science and Engineering"
    subject_ids: Optional[List[int]] = []

    @field_validator("name")
    @classmethod
    def validate_instructor_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Instructor name cannot be empty.")
        return value


class InstructorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    is_active: Optional[bool] = None
    subject_ids: Optional[List[int]] = None


class SimpleSubject(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    semester: int = 1

    class Config:
        from_attributes = True


class InstructorResponse(BaseModel):
    id: int
    name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    subjects: List[SimpleSubject] = []

    class Config:
        from_attributes = True


# ==========================================================
# STUDENT FEEDBACK SUBMISSION SCHEMAS
# ==========================================================

class FeedbackCreate(BaseModel):
    register_number: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="Student Register Number",
    )
    student_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Student Full Name",
    )
    department_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Department Name or Other",
    )
    subject_name: Optional[str] = Field(
        None,
        max_length=150,
        description="Subject name; null for Other",
    )
    semester: Optional[int] = Field(
        None,
        ge=1,
        le=8,
        description="Required for academic feedback; null for Other",
    )
    instructor_name: Optional[str] = Field(
        None,
        max_length=120,
        description="Instructor name; null for Other",
    )
    rating: int = Field(..., ge=1, le=5)
    feedback_text: str = Field(..., min_length=5, max_length=2000)

    @field_validator(
        "register_number",
        "student_name",
        "department_name",
        "feedback_text",
    )
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty or only whitespace.")
        return value

    @model_validator(mode="after")
    def validate_department_and_academics(self):
        department = self.department_name.strip()

        if department.lower() == "other":
            if self.subject_name and self.subject_name.strip():
                raise ValueError(
                    "Feedback under Other must not include a subject."
                )

            if self.instructor_name and self.instructor_name.strip():
                raise ValueError(
                    "Feedback under Other must not include an instructor."
                )

            self.subject_name = None
            self.instructor_name = None
            self.semester = None

        else:
            if self.semester is None:
                raise ValueError(
                    "Semester is required for academic feedback."
                )

            if not self.subject_name or not self.subject_name.strip():
                raise ValueError(
                    f"Subject name is required for department '{department}'."
                )

            if not self.instructor_name or not self.instructor_name.strip():
                raise ValueError(
                    f"Instructor name is required for department '{department}'."
                )

            self.subject_name = self.subject_name.strip()
            self.instructor_name = self.instructor_name.strip()

        return self


class SentimentScores(BaseModel):
    negative: float
    neutral: float
    positive: float


class FeedbackSubmissionResponse(BaseModel):
    id: int
    department_name: str
    is_other: bool
    subject_name: Optional[str] = None
    semester: Optional[int] = None
    instructor_name: Optional[str] = None
    rating: int
    feedback_text: str
    sentiment_label: str
    sentiment_detail: str
    sentiment_confidence: float
    is_mixed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================================
# ADMIN FEEDBACK SCHEMAS
# Student register numbers and names remain excluded.
# ==========================================================

class FeedbackAdminItem(BaseModel):
    id: int
    department_name: str
    is_other: bool
    subject_name: Optional[str] = None
    semester: Optional[int] = None
    instructor_name: Optional[str] = None
    rating: int
    feedback_text: str
    sentiment_label: str
    sentiment_detail: str
    sentiment_confidence: float
    sentiment_scores: Optional[Dict[str, float]] = None
    is_mixed: bool
    cluster_id: Optional[int] = None
    topic_label: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================================
# ANALYTICS SCHEMAS
# ==========================================================

class SentimentCount(BaseModel):
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    mixed: int = 0


class TopicClusterResponse(BaseModel):
    cluster_id: int
    topic_label: str
    comment_count: int
    sentiment_distribution: Dict[str, int]
    representative_comments: List[str]
    supporting_comments: List[FeedbackAdminItem]
    top_keywords: List[str]
    departments: List[str] = []
    subjects: List[str] = []
    instructors: List[str] = []


class OverviewMetrics(BaseModel):
    total_submissions: int
    sentiment_counts: SentimentCount
    rating_distribution: Dict[int, int]
    instructor_count: int
    topic_count: int
