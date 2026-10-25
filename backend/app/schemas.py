from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator

# --- Department Schemas ---

class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_str = v.strip()
        if not v_str:
            raise ValueError("Department name cannot be empty")
        return v_str

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

# --- Subject Schemas ---

class SubjectBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)
    department_id: int

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_str = v.strip()
        if not v_str:
            raise ValueError("Subject name cannot be empty")
        return v_str

class SubjectCreate(SubjectBase):
    instructor_ids: Optional[List[int]] = []

class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    code: Optional[str] = Field(None, max_length=20)
    department_id: Optional[int] = None
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
    code: Optional[str]
    department_id: Optional[int]
    department_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    instructors: List[SimpleInstructor] = []

    class Config:
        from_attributes = True

# --- Instructor Schemas ---

class InstructorCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    department_id: Optional[int] = None
    department_name: Optional[str] = "Computer Science and Engineering"
    subject_ids: Optional[List[int]] = []

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v_str = v.strip()
        if not v_str:
            raise ValueError("Instructor name cannot be empty")
        return v_str

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

# --- Student Submission Schemas ---

class FeedbackCreate(BaseModel):
    register_number: str = Field(..., min_length=2, max_length=50, description="Student Register Number")
    student_name: str = Field(..., min_length=2, max_length=150, description="Student Full Name")
    department_name: str = Field(..., min_length=2, max_length=150, description="Department Name or 'Other'")
    subject_name: Optional[str] = Field(None, max_length=150, description="Subject Name (null for Other)")
    instructor_name: Optional[str] = Field(None, max_length=120, description="Instructor Name (null for Other)")
    rating: int = Field(..., ge=1, le=5, description="Integer rating from 1 to 5")
    feedback_text: str = Field(..., min_length=5, max_length=2000, description="Written feedback")

    @field_validator('register_number', 'student_name', 'department_name', 'feedback_text')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        v_stripped = v.strip()
        if not v_stripped:
            raise ValueError("Field cannot be empty or only whitespace")
        return v_stripped

    @model_validator(mode='after')
    def validate_department_and_academics(self):
        dept = self.department_name.strip()
        if dept.lower() == 'other':
            # Other feedback must NOT have subject or instructor
            if self.subject_name and self.subject_name.strip():
                raise ValueError("Institutional feedback under 'Other' category must not include a Subject.")
            if self.instructor_name and self.instructor_name.strip():
                raise ValueError("Institutional feedback under 'Other' category must not include an Instructor.")
            self.subject_name = None
            self.instructor_name = None
        else:
            # Academic department feedback MUST have both subject and instructor
            if not self.subject_name or not self.subject_name.strip():
                raise ValueError(f"Subject Name is required for department '{dept}'.")
            if not self.instructor_name or not self.instructor_name.strip():
                raise ValueError(f"Instructor Name is required for department '{dept}'.")
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

# --- Admin View Schemas (Student Privacy Preserved) ---

class FeedbackAdminItem(BaseModel):
    id: int
    department_name: str
    is_other: bool
    subject_name: Optional[str] = None
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
