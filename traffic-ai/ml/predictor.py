import pickle
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / 'models' / 'congestion_model.pkl'


class CongestionPredictor:
    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = model_path
        self.available = False
        self.error_message = ''
        self.model = None
        self.feature_columns: list[str] = []
        self.training_accuracy: float | None = None
        self.labels: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            self.error_message = 'ML model not trained yet. Run ml/train_model.py first.'
            return

        try:
            with self.model_path.open('rb') as file_obj:
                payload = pickle.load(file_obj)
        except Exception as exc:
            self.error_message = f'Failed to load ML model: {exc}'
            return

        self.model = payload.get('pipeline')
        self.feature_columns = list(payload.get('feature_columns', []))
        self.training_accuracy = payload.get('accuracy')
        self.labels = list(payload.get('labels', []))
        self.available = self.model is not None
        if not self.available:
            self.error_message = 'ML model file is missing a pipeline object.'

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        if not self.available or self.model is None:
            return {
                'enabled': False,
                'label': 'Unavailable',
                'confidence': None,
                'training_accuracy': self.training_accuracy,
                'message': self.error_message,
            }

        sample = {column: features.get(column) for column in self.feature_columns}

        try:
            label = self.model.predict([sample])[0]
            confidence = None
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba([sample])[0]
                confidence = round(float(max(probabilities)) * 100.0, 1)
        except Exception as exc:
            return {
                'enabled': False,
                'label': 'Unavailable',
                'confidence': None,
                'training_accuracy': self.training_accuracy,
                'message': f'ML prediction failed: {exc}',
            }

        return {
            'enabled': True,
            'label': str(label),
            'confidence': confidence,
            'training_accuracy': round(float(self.training_accuracy) * 100.0, 1)
            if self.training_accuracy is not None
            else None,
            'message': 'Congestion forecast ready',
        }
