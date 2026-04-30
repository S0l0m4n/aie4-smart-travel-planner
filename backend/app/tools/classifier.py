import numpy as np
from pydantic import BaseModel, Field

from app.schemas.classify import DestinationFeatures

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


def classify_travel_style(features: DestinationFeatures, classifier) -> str:
    X = np.array([[getattr(features, f) for f in FEATURE_ORDER]])
    return str(classifier.predict(X)[0])
