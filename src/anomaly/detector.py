"""Detection d'anomalies non supervisee par Isolation Forest.

Le choix du non supervise est impose par le contexte : au demarrage du projet,
aucun historique de pannes etiquete n'etait disponible. Le modele est donc
entraine uniquement sur des fenetres considerees saines (baseline).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from src.features.vibration import FEATURE_NAMES


@dataclass
class AnomalyDetector:
    """Isolation Forest + normalisation, entraine sur une baseline saine."""

    features: list[str] = None
    contamination: float = 0.05
    n_estimators: int = 200
    random_state: int = 42

    def __post_init__(self) -> None:
        self.features = self.features or list(FEATURE_NAMES)
        self.scaler = StandardScaler()
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        self._fitted = False

    def fit(self, df_healthy: pd.DataFrame) -> "AnomalyDetector":
        """Entraine le modele sur des fenetres en etat nominal.

        Args:
            df_healthy: DataFrame contenant au moins les colonnes de self.features.
        """
        missing = set(self.features) - set(df_healthy.columns)
        if missing:
            raise KeyError(f"colonnes manquantes dans la baseline : {sorted(missing)}")

        x = self.scaler.fit_transform(df_healthy[self.features])
        self.model.fit(x)
        self._fitted = True
        return self

    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Annote un DataFrame avec le score d'anomalie et le drapeau booleen.

        Le score de `decision_function` est positif pour un point nominal,
        negatif pour un point isole (anormal).
        """
        if not self._fitted:
            raise RuntimeError("le modele doit etre entraine avant scoring")

        x = self.scaler.transform(df[self.features])
        out = df.copy()
        out["anomaly_score"] = self.model.decision_function(x)
        out["is_anomaly"] = self.model.predict(x) == -1
        return out

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"scaler": self.scaler, "model": self.model, "features": self.features}, path)

    @classmethod
    def load(cls, path: str | Path) -> "AnomalyDetector":
        payload = joblib.load(path)
        detector = cls(features=payload["features"])
        detector.scaler = payload["scaler"]
        detector.model = payload["model"]
        detector._fitted = True
        return detector


def rolling_baseline(df: pd.DataFrame, n_windows: int = 500) -> pd.DataFrame:
    """Selectionne les premieres fenetres comme baseline.

    Hypothese forte : l'equipement etait sain durant cette periode. En production,
    cette selection doit etre validee par le service maintenance, pas prise
    automatiquement -- sans quoi un defaut deja present devient la norme.
    """
    if len(df) < n_windows:
        raise ValueError(f"baseline trop courte : {len(df)} fenetres pour {n_windows} demandees")
    return df.iloc[:n_windows]
