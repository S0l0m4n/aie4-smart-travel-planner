from pathlib import Path

import joblib

from app.schemas.classify import DestinationFeatures

class MLClassifier:
    def __init__(self, path: Path) -> None:
        self.model = joblib.load(path)

    def predict(self, features: DestinationFeatures) -> str:
        # Convert features into an array of values
        x = [ list(features.model_dump().values()) ]
        return str(self.model.predict(x)[0])
