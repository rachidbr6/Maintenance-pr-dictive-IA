"""Frequences caracteristiques de defauts de roulement et severite ISO 20816-3.

Les formules suivent Randall, *Vibration-based Condition Monitoring* (Wiley, 2011).
ATTENTION : la geometrie des roulements du catalogue ci-dessous doit etre verifiee
contre la fiche constructeur avant tout usage terrain. Un nombre de billes ou un
diametre de bille errone decale toutes les frequences de defaut.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Bearing:
    """Geometrie d'un roulement a billes.

    Attributes:
        name: designation constructeur (ex. "SKF 6317").
        n_balls: nombre d'elements roulants Z.
        ball_diameter_mm: diametre d'un element roulant d.
        pitch_diameter_mm: diametre primitif D (moyenne alesage / diametre exterieur).
        contact_angle_deg: angle de contact alpha (0 pour un roulement rigide a billes).
    """

    name: str
    n_balls: int
    ball_diameter_mm: float
    pitch_diameter_mm: float
    contact_angle_deg: float = 0.0

    @property
    def ratio(self) -> float:
        """d/D * cos(alpha)."""
        return (self.ball_diameter_mm / self.pitch_diameter_mm) * math.cos(
            math.radians(self.contact_angle_deg)
        )


# Geometries indicatives -- A VERIFIER au catalogue avant exploitation.
CATALOG: dict[str, Bearing] = {
    "SKF 6317": Bearing("SKF 6317", n_balls=8, ball_diameter_mm=34.93, pitch_diameter_mm=132.5),
    "SKF 6205": Bearing("SKF 6205", n_balls=9, ball_diameter_mm=7.94, pitch_diameter_mm=39.04),
    "SKF 6203": Bearing("SKF 6203", n_balls=8, ball_diameter_mm=6.75, pitch_diameter_mm=28.50),
}


def fault_frequencies(bearing: Bearing, shaft_speed_hz: float) -> dict[str, float]:
    """Retourne BPFO, BPFI, BSF et FTF en Hz pour une vitesse d'arbre donnee.

    Args:
        bearing: geometrie du roulement.
        shaft_speed_hz: vitesse de rotation de l'arbre fr, en Hz (tr/min / 60).

    Returns:
        Dictionnaire {nom_frequence: valeur_hz}.
    """
    fr = shaft_speed_hz
    z = bearing.n_balls
    k = bearing.ratio

    return {
        "BPFO": (z / 2) * fr * (1 - k),
        "BPFI": (z / 2) * fr * (1 + k),
        "BSF": (bearing.pitch_diameter_mm / (2 * bearing.ball_diameter_mm)) * fr * (1 - k**2),
        "FTF": (fr / 2) * (1 - k),
    }


def fault_orders(bearing: Bearing) -> dict[str, float]:
    """Ordres (multiples de fr) des frequences de defaut -- utiles pour un controle rapide."""
    return {name: value for name, value in fault_frequencies(bearing, 1.0).items()}


# ISO 20816-3, machines > 15 kW, montage rigide. Vitesse vibratoire efficace en mm/s.
ISO_20816_3_ZONES = (
    (2.3, "A", "Bon - surveillance normale"),
    (4.5, "B", "Acceptable - surveillance rapprochee"),
    (7.1, "C", "Alerte - intervention a planifier"),
    (float("inf"), "D", "Danger - arret a envisager"),
)


def iso_zone(velocity_rms_mm_s: float) -> tuple[str, str]:
    """Classe une vitesse vibratoire RMS dans les zones ISO 20816-3.

    Args:
        velocity_rms_mm_s: vitesse vibratoire efficace en mm/s (bande 10-1000 Hz).

    Returns:
        Couple (zone, recommandation).
    """
    for threshold, zone, advice in ISO_20816_3_ZONES:
        if velocity_rms_mm_s < threshold:
            return zone, advice
    raise ValueError("valeur de vitesse vibratoire invalide")


def match_peak(
    peak_hz: float,
    bearing: Bearing,
    shaft_speed_hz: float,
    tolerance: float = 0.02,
    max_harmonic: int = 3,
) -> tuple[str, int, float] | None:
    """Cherche a quel defaut (et quelle harmonique) correspond un pic spectral.

    Args:
        peak_hz: frequence du pic detecte.
        bearing: geometrie du roulement instrumente.
        shaft_speed_hz: vitesse d'arbre mesuree au moment de l'acquisition.
        tolerance: ecart relatif maximal accepte (2 % par defaut).
        max_harmonic: rang harmonique maximal teste.

    Returns:
        (nom_defaut, rang_harmonique, erreur_relative) ou None si aucune correspondance.
    """
    best: tuple[str, int, float] | None = None

    for name, f0 in fault_frequencies(bearing, shaft_speed_hz).items():
        for harmonic in range(1, max_harmonic + 1):
            expected = harmonic * f0
            if expected <= 0:
                continue
            error = abs(peak_hz - expected) / expected
            if error <= tolerance and (best is None or error < best[2]):
                best = (name, harmonic, error)

    return best
