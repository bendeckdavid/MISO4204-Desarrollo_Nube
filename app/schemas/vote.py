"""Vote schemas"""
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


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

    position: int = Field(..., description="Player's position in ranking")
    username: str = Field(..., description="Player's full name")
    city: str = Field(..., description="Player's city")
    country: str = Field(..., description="Player's country")
    votes: int = Field(..., description="Total votes received")

    class Config:
        from_attributes = True


class RankingResponse(BaseModel):
    """Ranking response with pagination info"""

    rankings: List[RankingEntry] = Field(..., description="List of ranked players")
    total: int = Field(..., description="Total number of players in ranking")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "rankings": [
                    {
                        "position": 1,
                        "username": "Juan Pérez",
                        "city": "Bogotá",
                        "country": "Colombia",
                        "votes": 1530,
                    },
                    {
                        "position": 2,
                        "username": "María López",
                        "city": "Bogotá",
                        "country": "Colombia",
                        "votes": 1495,
                    },
                ],
                "total": 150,
                "page": 1,
                "page_size": 20,
                "total_pages": 8,
            }
        }
