
import hmac
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FeedbackSubmission
from app.routes.auth import ADMIN_PASSWORD, verify_session_token

router = APIRouter(
    prefix="/api/admin/feedback-data",
    tags=["Admin Feedback Data"],
)


class FeedbackScope(BaseModel):
    department_name: Optional[str] = Field(default=None, max_length=150)
    semester: Optional[int] = Field(default=None, ge=1, le=8)
    subject_name: Optional[str] = Field(default=None, max_length=150)
    instructor_name: Optional[str] = Field(default=None, max_length=120)


class DeleteFeedbackRequest(FeedbackScope):
    admin_password: str = Field(min_length=1, max_length=256)
    cutoff_created_at: Optional[datetime] = None


def require_admin(
    authorization: Optional[str] = Header(default=None),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Admin login is required.")

    token = authorization.split(" ", 1)[1].strip()
    if not verify_session_token(token):
        raise HTTPException(
            status_code=401,
            detail="Admin session is invalid or expired. Please log in again.",
        )

    return True


def filtered_feedback_query(db: Session, scope: FeedbackScope):
    query = db.query(FeedbackSubmission)

    department = (scope.department_name or "").strip()
    subject = (scope.subject_name or "").strip()
    instructor = (scope.instructor_name or "").strip()

    if department:
        if department.lower() == "other":
            query = query.filter(
                (FeedbackSubmission.department_name == "Other")
                | (FeedbackSubmission.is_other.is_(True))
            )
        else:
            query = query.filter(
                FeedbackSubmission.department_name.ilike(department)
            )

    # "Other" is general institutional feedback, not semester-based feedback.
    if department.lower() == "other" and (
        scope.semester is not None or subject or instructor
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "For Other institutional feedback, semester, subject, "
                "and instructor filters cannot be selected."
            ),
        )

    if scope.semester is not None:
        query = query.filter(
            FeedbackSubmission.semester == scope.semester
        )

    if subject:
        query = query.filter(
            FeedbackSubmission.subject_name.ilike(subject)
        )

    if instructor:
        query = query.filter(
            FeedbackSubmission.instructor_name.ilike(instructor)
        )

    return query


def scope_description(scope: FeedbackScope) -> str:
    parts = []

    if scope.department_name:
        parts.append(f"Department: {scope.department_name}")
    if scope.semester is not None:
        parts.append(f"Semester: {scope.semester}")
    if scope.subject_name:
        parts.append(f"Subject: {scope.subject_name}")
    if scope.instructor_name:
        parts.append(f"Instructor: {scope.instructor_name}")

    return " | ".join(parts) if parts else "All feedback records"


def create_pdf(records, scope: FeedbackScope, generated_at: datetime) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from xml.sax.saxutils import escape
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="PDF support is missing. Install it using: pip install reportlab",
        ) from exc

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="StuFeed Feedback Report",
    )

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="StuFeedTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )
    cell = ParagraphStyle(
        "FeedbackCell",
        parent=styles["BodyText"],
        fontSize=7.5,
        leading=9,
        spaceAfter=0,
    )

    story = [
        Paragraph("StuFeed — Feedback Report", styles["StuFeedTitle"]),
        Paragraph(
            f"<b>Selected scope:</b> {escape(scope_description(scope))}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Generated at (UTC):</b> "
            f"{generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            styles["BodyText"],
        ),
        Paragraph(
            f"<b>Total matching records:</b> {len(records)}",
            styles["BodyText"],
        ),
        Spacer(1, 8),
    ]

    headers = [
        "Date", "Department", "Semester", "Subject",
        "Instructor", "Rating", "Sentiment", "Feedback",
    ]
    data = [[Paragraph(f"<b>{h}</b>", cell) for h in headers]]

    for record in records:
        feedback = escape(record.feedback_text or "").replace("\n", "<br/>")
        department = record.department_name or (
            "Other" if record.is_other else "—"
        )

        values = [
            record.created_at.strftime("%Y-%m-%d")
            if record.created_at else "—",
            department,
            str(record.semester) if record.semester is not None else "—",
            record.subject_name or "—",
            record.instructor_name or "—",
            str(record.rating),
            record.sentiment_label or "—",
            feedback,
        ]
        data.append([Paragraph(escape(str(v)) if i != 7 else v, cell)
                     for i, v in enumerate(values)])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            22 * mm, 34 * mm, 18 * mm, 35 * mm,
            35 * mm, 15 * mm, 25 * mm, 95 * mm,
        ],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    document.build(story)

    return buffer.getvalue()


@router.post("/report")
def download_feedback_report(
    scope: FeedbackScope,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Capture a cutoff so report-then-delete cannot include later submissions.
    cutoff = datetime.utcnow()

    records = (
        filtered_feedback_query(db, scope)
        .filter(FeedbackSubmission.created_at <= cutoff)
        .order_by(
            FeedbackSubmission.created_at.asc(),
            FeedbackSubmission.id.asc(),
        )
        .all()
    )

    pdf = create_pdf(records, scope, cutoff)
    filename = f"stufeed_feedback_report_{cutoff:%Y%m%d_%H%M%S}.pdf"

    response = StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
    )
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )
    response.headers["X-Report-Cutoff-UTC"] = cutoff.isoformat()
    response.headers["Access-Control-Expose-Headers"] = (
        "Content-Disposition, X-Report-Cutoff-UTC"
    )
    return response


@router.post("/delete")
def delete_selected_feedback(
    payload: DeleteFeedbackRequest,
    _admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Require the current admin password again before deleting anything.
    if not ADMIN_PASSWORD or not hmac.compare_digest(
        payload.admin_password, ADMIN_PASSWORD
    ):
        raise HTTPException(
            status_code=401,
            detail="Admin password is incorrect.",
        )

    scope = FeedbackScope(
        department_name=payload.department_name,
        semester=payload.semester,
        subject_name=payload.subject_name,
        instructor_name=payload.instructor_name,
    )

    query = filtered_feedback_query(db, scope)

    # Used only after the report has been generated and downloaded.
    if payload.cutoff_created_at is not None:
        query = query.filter(
            FeedbackSubmission.created_at <= payload.cutoff_created_at
        )

    matching_count = query.count()

    if matching_count == 0:
        return {
            "deleted_count": 0,
            "message": "No feedback matched the selected scope.",
        }

    # IMPORTANT: delete feedback submissions only.
    # Do not delete StudentRecord, Department, Subject, or Instructor rows.
    deleted_count = query.delete(synchronize_session=False)
    db.commit()

    return {
        "deleted_count": deleted_count,
        "message": f"Deleted {deleted_count} feedback record(s).",
    }
