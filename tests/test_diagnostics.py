"""Tests des briques de diagnostic."""

import numpy as np
import pandas as pd
import pytest

from src.anomaly.detector import AnomalyDetector
from src.diagnostics.bearing import CATALOG, fault_frequencies, iso_zone, match_peak
from src.features.vibration import envelope_spectrum, extract_features, time_domain_features
from scripts.generate_signal import synth_signal

FS = 25_600.0
SPEED = 24.8
BEARING = CATALOG["SKF 6317"]


def test_fault_frequency_ordering():
    """BPFI > BPFO > BSF > FTF pour un roulement rigide a billes."""
    f = fault_frequencies(BEARING, SPEED)
    assert f["BPFI"] > f["BPFO"] > f["BSF"] > f["FTF"]


def test_bpfo_order_is_physically_plausible():
    """L'ordre du BPFO vaut Z/2 * (1 - d/D), soit ~2,9 pour un 6317 (Z=8)."""
    order = fault_frequencies(BEARING, 1.0)["BPFO"]
    assert 2.5 < order < 3.5, f"ordre BPFO invraisemblable : {order:.2f}"


def test_ftf_below_shaft_speed():
    """La cage tourne toujours plus lentement que l'arbre."""
    assert fault_frequencies(BEARING, SPEED)["FTF"] < SPEED


@pytest.mark.parametrize(
    "velocity,expected",
    [(1.0, "A"), (3.0, "B"), (5.0, "C"), (9.0, "D")],
)
def test_iso_zones(velocity, expected):
    assert iso_zone(velocity)[0] == expected


def test_kurtosis_of_gaussian_noise_is_three():
    rng = np.random.default_rng(0)
    stats = time_domain_features(rng.normal(size=200_000))
    assert stats["kurtosis"] == pytest.approx(3.0, abs=0.1)


def test_envelope_recovers_injected_bpfo():
    """Test de bout en bout : un defaut BPFO injecte doit ressortir du spectre d'enveloppe."""
    signal = synth_signal(fs=FS, duration_s=2.0, shaft_speed_hz=SPEED, fault="bpfo")
    freqs, amps = envelope_spectrum(signal, FS)

    expected = fault_frequencies(BEARING, SPEED)["BPFO"]
    window = (freqs > expected - 5) & (freqs < expected + 5)
    peak_hz = float(freqs[window][np.argmax(amps[window])])

    hit = match_peak(peak_hz, BEARING, SPEED)
    assert hit is not None and hit[0] == "BPFO"


def test_fault_raises_kurtosis():
    """Le kurtosis doit distinguer un signal sain d'un signal impulsionnel."""
    healthy = synth_signal(fs=FS, duration_s=1.0, shaft_speed_hz=SPEED)
    faulty = synth_signal(fs=FS, duration_s=1.0, shaft_speed_hz=SPEED, fault="bpfo")

    assert time_domain_features(healthy)["kurtosis"] < 4
    assert time_domain_features(faulty)["kurtosis"] > 6


def _feature_frame(n: int, fault: str | None, seed_offset: int = 0) -> pd.DataFrame:
    rows = [
        extract_features(
            synth_signal(fs=FS, duration_s=1.0, shaft_speed_hz=SPEED, fault=fault, seed=i + seed_offset),
            FS,
            BEARING,
            SPEED,
        )
        for i in range(n)
    ]
    return pd.DataFrame(rows)


def test_detector_flags_faulty_windows():
    """Entraine sur du sain, teste sur du defectueux : les anomalies doivent sortir."""
    detector = AnomalyDetector(contamination=0.05).fit(_feature_frame(30, None))
    flagged = detector.score(_feature_frame(10, "bpfo", seed_offset=100))["is_anomaly"]
    assert flagged.mean() >= 0.8


def test_detector_low_false_positive_on_healthy():
    detector = AnomalyDetector(contamination=0.05).fit(_feature_frame(30, None))
    flagged = detector.score(_feature_frame(15, None, seed_offset=500))["is_anomaly"]
    assert flagged.mean() <= 0.2
