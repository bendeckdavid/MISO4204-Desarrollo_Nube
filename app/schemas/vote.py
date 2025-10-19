"""Vote schemas"""

from pydantic import BaseModel, Field
from datetime import datetime


class VoteResponse(BaseModel):
    """Response after voting"""

    message: str = Field(..., example="Voto registrado exitosamente.")
    video_id: str
    total_votes: int


class PublicVideoResponse(BaseModel):
    """Public video details for voting"""

    video_id: str
    title: str
    player_name: str
    city: str
    country: str
    processed_url: str
    votes: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


class RankingEntry(BaseModel):
    """Single ranking entry"""

    position: int
    username: str
    city: str
    country: str
    votes: int
    video_id: str

    class Config:
        from_attributes = True


class RankingResponse(BaseModel):
    """Ranking response with pagination info"""

    rankings: list[RankingEntry]
    total: int
    page: int
    page_size: int
    total_pages: int
