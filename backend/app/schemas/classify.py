from pydantic import BaseModel, Field
from typing import Literal


class DestinationFeatures(BaseModel):
    hiking_score: float | None = Field(default=None, ge=1, le=10)
    beach_score: float | None = Field(default=None, ge=1, le=10)
    cultural_sites_score: float | None = Field(default=None, ge=1, le=10)
    nightlife_score: float | None = Field(default=None, ge=1, le=10)
    family_friendly_score: float | None = Field(default=None, ge=1, le=10)
    luxury_infrastructure_score: float | None = Field(default=None, ge=1, le=10)
    avg_accom_cost: float | None = Field(default=None, ge=0)
    avg_daily_expense: float | None = Field(default=None, ge=0)
    safety_score: float | None = Field(default=None, ge=1, le=10)
    remoteness_score: float | None = Field(default=None, ge=1, le=10)


class ClassifyResponse(BaseModel):
    label: Literal["Adventure", "Budget", "Culture", "Family", "Luxury", "Relaxation"]
