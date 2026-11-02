"""Extraction des indicateurs vibratoires (domaine temporel et spectral).

Ce module produit le vecteur de features consomme par le detecteur d'anomalies
et par la couche de diagnostic.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import hilbert, butter, sosfiltfilt

from src.diagnostics.bearing import Bearing, fault_frequencies

FEATURE_NAMES = [
    "rms",
    "kurtosis",
    "crest_factor",
    "peak_to_peak",
    "bpfo_level",
    "bpfi_level",
]


def time_domain_features(signal: np.ndarray) -> dict[str, float]:
    """Indicateurs statistiques classiques sur une fenetre de signal.

    Le kurtosis vaut ~3 pour un signal gaussien ; une valeur > 6 signale des
    impulsions transitoires typiques d'un ecaillage de roulement.
    """
    x = np.asarray(signal, dtype=float)
    rms = float(np.sqrt(np.mean(x**2)))
    sigma = float(np.std(x))
    mean = float(np.mean(x))

    kurtosis = float(np.mean((x - mean) ** 4) / sigma**4) if sigma > 0 else 0.0
    crest = float(np.max(np.abs(x)) / rms) if rms > 0 else 0.0

    return {
        "rms": rms,
        "kurtosis": kurtosis,
        "crest_factor": crest,
        "peak_to_peak": float(np.ptp(x)),
    }


def spectrum(signal: np.ndarray, fs: float, n_avg: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """FFT monolaterale avec fenetre de Hann, et moyennage optionnel.

    Le moyennage (n_avg blocs, recouvrement 50 %) reduit la variance du plancher
    de bruit d'un facteur sqrt(n_avg) au prix de la resolution frequentielle.
    Sur un spectre d'enveloppe c'est decisif : sans lui, les raies de defaut se
    confondent avec les pics de bruit.

    Returns:
        (frequences_hz, amplitudes) -- amplitudes a l'echelle du signal d'entree.
    """
    x = np.asarray(signal, dtype=float)
    x = x - x.mean()

    if n_avg <= 1:
        segments = [x]
        seg_len = len(x)
    else:
        seg_len = len(x) // ((n_avg + 1) // 2)
        step = seg_len // 2
        segments = [x[i : i + seg_len] for i in range(0, len(x) - seg_len + 1, step)]

    window = np.hanning(seg_len)
    acc = np.zeros(seg_len // 2 + 1)
    for seg in segments:
        acc += np.abs(np.fft.rfft(seg * window)) ** 2
    spec = np.sqrt(acc / len(segments)) * 2 / np.sum(window)

    freqs = np.fft.rfftfreq(seg_len, d=1 / fs)
    return freqs, spec


def envelope_spectrum(
    signal: np.ndarray,
    fs: float,
    band_hz: tuple[float, float] = (3000.0, 10000.0),
    n_avg: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Spectre d'enveloppe : filtrage passe-bande, demodulation de Hilbert, FFT.

    C'est la methode de reference pour les defauts embryonnaires de roulement,
    invisibles en FFT directe car noyes sous les composantes basse frequence.

    Args:
        signal: signal vibratoire brut (acceleration).
        fs: frequence d'echantillonnage en Hz.
        band_hz: bande de resonance a demoduler.
        n_avg: nombre de blocs moyennes (voir `spectrum`).
    """
    low, high = band_hz
    nyquist = fs / 2
    if high >= nyquist:
        high = 0.95 * nyquist

    sos = butter(4, [low / nyquist, high / nyquist], btype="bandpass", output="sos")
    filtered = sosfiltfilt(sos, np.asarray(signal, dtype=float))
    envelope = np.abs(hilbert(filtered))
    return spectrum(envelope, fs, n_avg=n_avg)


def band_level(freqs: np.ndarray, amps: np.ndarray, target_hz: float, half_width_hz: float = 3.0) -> float:
    """Amplitude maximale dans une bande etroite centree sur une frequence cible."""
    mask = (freqs >= target_hz - half_width_hz) & (freqs <= target_hz + half_width_hz)
    return float(amps[mask].max()) if mask.any() else 0.0


def extract_features(
    signal: np.ndarray,
    fs: float,
    bearing: Bearing,
    shaft_speed_hz: float,
) -> dict[str, float]:
    """Vecteur de features complet pour une fenetre d'acquisition.

    Combine indicateurs temporels et niveaux spectraux d'enveloppe aux frequences
    BPFO / BPFI, ce qui donne au detecteur d'anomalies une information deja
    orientee defaut de roulement plutot que purement statistique.
    """
    features = time_domain_features(signal)
    env_freqs, env_amps = envelope_spectrum(signal, fs)
    faults = fault_frequencies(bearing, shaft_speed_hz)

    features["bpfo_level"] = band_level(env_freqs, env_amps, faults["BPFO"])
    features["bpfi_level"] = band_level(env_freqs, env_amps, faults["BPFI"])
    return features


def top_peaks(freqs: np.ndarray, amps: np.ndarray, n: int = 5, min_hz: float = 5.0, min_separation_hz: float = 4.0) -> list[tuple[float, float]]:
    """Retourne les n pics les plus energetiques au-dessus de min_hz.

    Les pics distants de moins de `min_separation_hz` sont fusionnes : sans cela,
    les quelques bins encadrant une meme raie saturent la liste et masquent les
    harmoniques suivantes.
    """
    mask = freqs >= min_hz
    f, a = freqs[mask], amps[mask]

    selected: list[int] = []
    for i in np.argsort(a)[::-1]:
        if all(abs(f[i] - f[j]) >= min_separation_hz for j in selected):
            selected.append(int(i))
        if len(selected) == n:
            break

    return [(float(f[i]), float(a[i])) for i in sorted(selected, key=lambda j: f[j])]
