import numpy as np
from pydantic import BaseModel, Field

FEATURE_ORDER = [
    "hiking_score",
    "beach_score",
    "cultural_sites_score",
    "nightlife_score",
    "family_friendly_score",
    "luxury_infrastructure_score",
    "avg_accom_cost",
    "avg_daily_expense",
    "safety_score",
    "remoteness_score",
]


class DestinationFeatures(BaseModel):
    hiking_score: float = Field(ge=1, le=10)
    beach_score: float = Field(ge=1, le=10)
    cultural_sites_score: float = Field(ge=1, le=10)
    nightlife_score: float = Field(ge=1, le=10)
    family_friendly_score: float = Field(ge=1, le=10)
    luxury_infrastructure_score: float = Field(ge=1, le=10)
    avg_accom_cost: float = Field(ge=0)
    avg_daily_expense: float = Field(ge=0)
    safety_score: float = Field(ge=1, le=10)
    remoteness_score: float = Field(ge=1, le=10)


def classify_travel_style(features: DestinationFeatures, classifier) -> str:
    X = np.array([[getattr(features, f) for f in FEATURE_ORDER]])
    return str(classifier.predict(X)[0])