import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import FeedbackSubmission, Instructor, Department
from app.schemas import OverviewMetrics, SentimentCount, TopicClusterResponse, FeedbackAdminItem
from app.nlp.pipeline import compute_topic_clusters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Intelligence"])

@router.get("/overview", response_model=OverviewMetrics)
def get_overview_metrics(
    department_name: Optional[str] = Query(None),
    subject_name: Optional[str] = Query(None),
    instructor_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Computes real summary metrics directly from database records respecting active filters.
    Never hardcoded or fabricated.
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

    total = query.count()

    pos_count = query.filter(FeedbackSubmission.sentiment_label == "Positive").count()
    neg_count = query.filter(FeedbackSubmission.sentiment_label == "Negative").count()
    neu_count = query.filter(FeedbackSubmission.sentiment_label == "Neutral").count()
    mixed_count = query.filter(FeedbackSubmission.is_mixed == True).count()

    # Rating distribution
    rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    r_stats = query.with_entities(
        FeedbackSubmission.rating, func.count(FeedbackSubmission.id)
    ).group_by(FeedbackSubmission.rating).all()

    for rating, count in r_stats:
        if rating in rating_counts:
            rating_counts[rating] = count

    # Instructor count
    inst_query = db.query(func.count(Instructor.id)).filter(Instructor.is_active == True)
    if department_name and department_name.strip() and department_name.strip().lower() != "other":
        dept = db.query(Department).filter(Department.name.ilike(department_name.strip())).first()
        if dept:
            inst_query = inst_query.filter(Instructor.department_id == dept.id)
    elif department_name and department_name.strip().lower() == "other":
        inst_query = None

    instructor_count = (inst_query.scalar() or 0) if inst_query is not None else 0

    # Topic count from actual submissions
    all_subs = query.all()
    topic_count = 0
    if len(all_subs) > 0:
        clusters = compute_topic_clusters(all_subs)
        topic_count = len(clusters)

    return OverviewMetrics(
        total_submissions=total,
        sentiment_counts=SentimentCount(
            positive=pos_count,
            negative=neg_count,
            neutral=neu_count,
            mixed=mixed_count
        ),
        rating_distribution=rating_counts,
        instructor_count=instructor_count,
        topic_count=topic_count
    )

@router.get("/topics", response_model=List[TopicClusterResponse])
def get_topic_intelligence(
    department_name: Optional[str] = Query(None),
    subject_name: Optional[str] = Query(None),
    instructor_name: Optional[str] = Query(None),
    sentiment_label: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Runs the real Sentence Transformer embedding and clustering pipeline on feedback submissions.
    Generates data-driven topic labels, includes department context, and returns supporting evidence.
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

    submissions = query.order_by(FeedbackSubmission.created_at.desc()).all()
    if not submissions:
        return []

    # Run clustering pipeline
    raw_clusters = compute_topic_clusters(submissions)

    # Format response
    formatted_clusters = []
    for c in raw_clusters:
        supp_items = []
        for s in c["supporting_comments"]:
            supp_items.append(FeedbackAdminItem(
                id=s["id"],
                department_name=s.get("department_name", "Other"),
                is_other=s.get("is_other", False),
                subject_name=s.get("subject_name"),
                instructor_name=s.get("instructor_name"),
                rating=s["rating"],
                feedback_text=s["feedback_text"],
                sentiment_label=s["sentiment_label"],
                sentiment_detail=s["sentiment_detail"],
                sentiment_confidence=s["sentiment_confidence"],
                sentiment_scores=s.get("sentiment_scores"),
                is_mixed=s.get("is_mixed", False),
                cluster_id=c["cluster_id"],
                topic_label=c["topic_label"],
                created_at=s["created_at"]
            ))

        formatted_clusters.append(TopicClusterResponse(
            cluster_id=c["cluster_id"],
            topic_label=c["topic_label"],
            comment_count=c["comment_count"],
            sentiment_distribution=c["sentiment_distribution"],
            representative_comments=c["representative_comments"],
            supporting_comments=supp_items,
            top_keywords=c["top_keywords"],
            departments=c.get("departments", []),
            subjects=c.get("subjects", []),
            instructors=c.get("instructors", [])
        ))

    return formatted_clusters

@router.get("/instructor-breakdown")
def get_instructor_breakdown(
    department_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns sentiment and feedback breakdown for each instructor with sufficient data.
    Avoids duplicate counting if an instructor teaches multiple subjects.
    """
    query = db.query(Instructor).filter(Instructor.is_active == True)

    if department_name and department_name.strip() and department_name.strip().lower() != "other":
        dept = db.query(Department).filter(Department.name.ilike(department_name.strip())).first()
        if dept:
            query = query.filter(Instructor.department_id == dept.id)
    elif department_name and department_name.strip().lower() == "other":
        # Other category has no instructors
        return []

    instructors = query.order_by(Instructor.name).all()
    breakdown = []

    for inst in instructors:
        subs = db.query(FeedbackSubmission).filter(
            FeedbackSubmission.instructor_name == inst.name
        ).all()

        dept_display = inst.department_name or (inst.department_rel.name if inst.department_rel else inst.department)

        if not subs:
            breakdown.append({
                "instructor_name": inst.name,
                "department": dept_display,
                "total_feedback": 0,
                "positive": 0,
                "negative": 0,
                "neutral": 0,
                "mixed": 0,
                "average_rating": 0.0
            })
            continue

        pos = sum(1 for s in subs if s.sentiment_label == "Positive")
        neg = sum(1 for s in subs if s.sentiment_label == "Negative")
        neu = sum(1 for s in subs if s.sentiment_label == "Neutral")
        mixed = sum(1 for s in subs if s.is_mixed)
        avg_rating = round(sum(s.rating for s in subs) / len(subs), 2)

        breakdown.append({
            "instructor_name": inst.name,
            "department": dept_display,
            "total_feedback": len(subs),
            "positive": pos,
            "negative": neg,
            "neutral": neu,
            "mixed": mixed,
            "average_rating": avg_rating
        })

    return breakdown
