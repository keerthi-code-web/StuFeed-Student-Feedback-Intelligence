
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import FeedbackSubmission, Instructor, Department
from app.schemas import (
    OverviewMetrics,
    SentimentCount,
    TopicClusterResponse,
    FeedbackAdminItem,
)
from app.nlp.pipeline import compute_topic_clusters


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics & Intelligence"],
)


def apply_feedback_filters(
    query,
    department_name: Optional[str] = None,
    subject_name: Optional[str] = None,
    instructor_name: Optional[str] = None,
    semester: Optional[int] = None,
    sentiment_label: Optional[str] = None,
):
    """Apply consistent filters to feedback queries."""

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

    return query


@router.get("/overview", response_model=OverviewMetrics)
def get_overview_metrics(
    department_name: Optional[str] = Query(None),
    subject_name: Optional[str] = Query(None),
    instructor_name: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=8),
    db: Session = Depends(get_db),
):
    """Calculate metrics from stored feedback records."""

    query = apply_feedback_filters(
        db.query(FeedbackSubmission),
        department_name=department_name,
        subject_name=subject_name,
        instructor_name=instructor_name,
        semester=semester,
    )

    total = query.count()

    positive_count = query.filter(
        FeedbackSubmission.sentiment_label == "Positive"
    ).count()

    negative_count = query.filter(
        FeedbackSubmission.sentiment_label == "Negative"
    ).count()

    neutral_count = query.filter(
        FeedbackSubmission.sentiment_label == "Neutral"
    ).count()

    mixed_count = query.filter(
        FeedbackSubmission.is_mixed.is_(True)
    ).count()

    rating_distribution = {
        1: 0,
        2: 0,
        3: 0,
        4: 0,
        5: 0,
    }

    rating_rows = query.with_entities(
        FeedbackSubmission.rating,
        func.count(FeedbackSubmission.id),
    ).group_by(FeedbackSubmission.rating).all()

    for rating, count in rating_rows:
        if rating in rating_distribution:
            rating_distribution[rating] = count

    instructor_query = db.query(Instructor).filter(
        Instructor.is_active.is_(True)
    )

    if department_name and department_name.strip():
        if department_name.strip().lower() == "other":
            instructor_query = None
        else:
            department = (
                db.query(Department)
                .filter(
                    Department.name.ilike(department_name.strip())
                )
                .first()
            )
            if department:
                instructor_query = instructor_query.filter(
                    Instructor.department_id == department.id
                )

    if instructor_query is None:
        instructor_count = 0
    else:
        instructor_count = instructor_query.count()

    # Cluster only the records included by the active filters.
    submissions = query.all()
    topic_count = 0

    if submissions:
        topic_count = len(compute_topic_clusters(submissions))

    return OverviewMetrics(
        total_submissions=total,
        sentiment_counts=SentimentCount(
            positive=positive_count,
            negative=negative_count,
            neutral=neutral_count,
            mixed=mixed_count,
        ),
        rating_distribution=rating_distribution,
        instructor_count=instructor_count,
        topic_count=topic_count,
    )


@router.get("/topics", response_model=List[TopicClusterResponse])
def get_topic_intelligence(
    department_name: Optional[str] = Query(None),
    subject_name: Optional[str] = Query(None),
    instructor_name: Optional[str] = Query(None),
    sentiment_label: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=8),
    db: Session = Depends(get_db),
):
    """
    Run the existing embedding and clustering pipeline only on
    feedback matching the selected filters and semester.
    """

    query = apply_feedback_filters(
        db.query(FeedbackSubmission),
        department_name=department_name,
        subject_name=subject_name,
        instructor_name=instructor_name,
        semester=semester,
        sentiment_label=sentiment_label,
    )

    submissions = query.order_by(
        FeedbackSubmission.created_at.desc()
    ).all()

    if not submissions:
        return []

    raw_clusters = compute_topic_clusters(submissions)
    formatted_clusters = []

    for cluster in raw_clusters:
        supporting_items = []

        for item in cluster["supporting_comments"]:
            supporting_items.append(
                FeedbackAdminItem(
                    id=item["id"],
                    department_name=item.get(
                        "department_name", "Other"
                    ),
                    is_other=item.get("is_other", False),
                    subject_name=item.get("subject_name"),
                    semester=item.get("semester"),
                    instructor_name=item.get("instructor_name"),
                    rating=item["rating"],
                    feedback_text=item["feedback_text"],
                    sentiment_label=item["sentiment_label"],
                    sentiment_detail=item["sentiment_detail"],
                    sentiment_confidence=item["sentiment_confidence"],
                    sentiment_scores=item.get("sentiment_scores"),
                    is_mixed=item.get("is_mixed", False),
                    cluster_id=cluster["cluster_id"],
                    topic_label=cluster["topic_label"],
                    created_at=item["created_at"],
                )
            )

        formatted_clusters.append(
            TopicClusterResponse(
                cluster_id=cluster["cluster_id"],
                topic_label=cluster["topic_label"],
                comment_count=cluster["comment_count"],
                sentiment_distribution=cluster[
                    "sentiment_distribution"
                ],
                representative_comments=cluster[
                    "representative_comments"
                ],
                supporting_comments=supporting_items,
                top_keywords=cluster["top_keywords"],
                departments=cluster.get("departments", []),
                subjects=cluster.get("subjects", []),
                instructors=cluster.get("instructors", []),
            )
        )

    return formatted_clusters


@router.get("/instructor-breakdown")
def get_instructor_breakdown(
    department_name: Optional[str] = Query(None),
    semester: Optional[int] = Query(None, ge=1, le=8),
    db: Session = Depends(get_db),
):
    """Return instructor statistics for the selected semester."""

    instructor_query = db.query(Instructor).filter(
        Instructor.is_active.is_(True)
    )

    if department_name and department_name.strip():
        clean_department = department_name.strip()

        if clean_department.lower() == "other":
            return []

        department = (
            db.query(Department)
            .filter(Department.name.ilike(clean_department))
            .first()
        )

        if department:
            instructor_query = instructor_query.filter(
                Instructor.department_id == department.id
            )

    instructors = instructor_query.order_by(Instructor.name).all()
    breakdown = []

    for instructor in instructors:
        feedback_query = db.query(FeedbackSubmission).filter(
            FeedbackSubmission.instructor_name == instructor.name
        )

        if semester is not None:
            feedback_query = feedback_query.filter(
                FeedbackSubmission.semester == semester
            )

        if department_name and department_name.strip():
            feedback_query = feedback_query.filter(
                FeedbackSubmission.department_name.ilike(
                    department_name.strip()
                )
            )

        submissions = feedback_query.all()

        department_display = (
            instructor.department_name
            or (
                instructor.department_rel.name
                if instructor.department_rel
                else instructor.department
            )
        )

        if not submissions:
            breakdown.append(
                {
                    "instructor_name": instructor.name,
                    "department": department_display,
                    "total_feedback": 0,
                    "positive": 0,
                    "negative": 0,
                    "neutral": 0,
                    "mixed": 0,
                    "average_rating": 0.0,
                }
            )
            continue

        positive_count = sum(
            1 for item in submissions
            if item.sentiment_label == "Positive"
        )
        negative_count = sum(
            1 for item in submissions
            if item.sentiment_label == "Negative"
        )
        neutral_count = sum(
            1 for item in submissions
            if item.sentiment_label == "Neutral"
        )
        mixed_count = sum(
            1 for item in submissions if item.is_mixed
        )

        average_rating = round(
            sum(item.rating for item in submissions)
            / len(submissions),
            2,
        )

        breakdown.append(
            {
                "instructor_name": instructor.name,
                "department": department_display,
                "total_feedback": len(submissions),
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count,
                "mixed": mixed_count,
                "average_rating": average_rating,
            }
        )

    return breakdown
