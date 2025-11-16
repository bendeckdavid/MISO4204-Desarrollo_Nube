"""Public endpoints for voting and rankings"""

import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import models
from app.db.database import get_db
from app.schemas.vote import PublicVideoResponse, RankingResponse, VoteResponse

router = APIRouter()


@router.get("/videos", response_model=List[PublicVideoResponse], status_code=status.HTTP_200_OK)
async def list_public_videos(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    db: Session = Depends(get_db),
):
    """
    List all public videos available for voting.

    Videos must be:
    - Processed successfully (status = 'processed' or 'completed')
    - Published (is_published = True)
    """

    query = (
        db.query(models.Video)
        .filter(models.Video.status.in_(["processed", "completed"]))
        .filter(models.Video.is_published.is_(True))
        .join(models.User)
    )

    videos = query.offset(skip).limit(limit).all()

    response = []
    for video in videos:
        response.append(
            {
                "video_id": str(video.id),
                "title": video.title,
                "player_name": f"{video.user.first_name} {video.user.last_name}",
                "city": video.user.city,
                "country": video.user.country,
                "processed_url": f"https://anb.com/videos/processed/{video.id}.mp4",
                "votes": video.vote_count,
                "uploaded_at": video.created_at,
            }
        )

    return response


@router.post("/videos/{video_id}/vote", response_model=VoteResponse, status_code=status.HTTP_200_OK)
async def vote_for_video(
    video_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cast a vote for a specific video.

    Rules:
    - User must be authenticated
    - One vote per user per video
    - Video must be published and processed
    """

    # Check if video exists and is published
    video = db.query(models.Video).filter(models.Video.id == video_id).first()

    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video no encontrado")

    if video.status not in ["processed", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este video no está disponible para votación",
        )

    # Check if user already voted for this video
    existing_vote = (
        db.query(models.Vote)
        .filter(models.Vote.user_id == current_user.id, models.Vote.video_id == video_id)
        .first()
    )

    if existing_vote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ya has votado por este video"
        )

    # Create new vote
    new_vote = models.Vote(user_id=current_user.id, video_id=video_id)

    db.add(new_vote)
    db.commit()

    # Get updated vote count
    total_votes = (
        db.query(func.count(models.Vote.id)).filter(models.Vote.video_id == video_id).scalar()
    )

    return {
        "message": "Voto registrado exitosamente.",
        "video_id": video_id,
        "total_votes": total_votes or 0,
    }


@router.get("/rankings", response_model=RankingResponse)
def get_rankings(
    city: Optional[str] = Query(None, description="Filter by city (e.g., 'Bogotá')"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
):
    """
    Get player rankings based on total votes.

    NO AUTHENTICATION REQUIRED - This is a public endpoint.

    Features:
    - Returns top players ordered by vote count (descending)
    - Supports pagination (page and page_size)
    - Optional filter by city

    Performance Note:
    ⚠️ For high-traffic production environments, consider implementing:
       - Redis caching with TTL (1-5 minutes)
       - PostgreSQL materialized views
       - Background job to pre-calculate rankings
    """

    # Build query: count votes per player
    query = (
        db.query(
            models.User.id,
            models.User.first_name,
            models.User.last_name,
            models.User.city,
            models.User.country,
            func.count(models.Vote.id).label("vote_count"),
        )
        .join(models.Video, models.User.id == models.Video.user_id)
        .outerjoin(models.Vote, models.Video.id == models.Vote.video_id)
        .filter(models.Video.status.in_(["processed", "completed"]))
        .filter(models.Video.is_published.is_(True))
        .group_by(
            models.User.id,
            models.User.first_name,
            models.User.last_name,
            models.User.city,
            models.User.country,
        )
    )

    # Apply city filter if provided
    if city:
        query = query.filter(models.User.city == city)

    # Order by votes descending
    query = query.order_by(desc("vote_count"))

    # Get total count for pagination
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    # Apply pagination
    skip = (page - 1) * page_size
    results = query.offset(skip).limit(page_size).all()

    # Build response with position numbers
    rankings = []
    for idx, result in enumerate(results, start=skip + 1):
        rankings.append(
            {
                "position": idx,
                "username": f"{result.first_name} {result.last_name}",
                "city": result.city,
                "country": result.country,
                "votes": result.vote_count,
            }
        )

    return {
        "rankings": rankings,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
