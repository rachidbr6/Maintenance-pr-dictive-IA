"""Genere un signal vibratoire synthetique (sain ou avec defaut BPFO).

Aucune donnee OCP n'est distribuee dans ce depot. Ce generateur produit des
signaux physiquement plausibles permettant de rejouer toute la chaine de
traitement sans acces a l'installation industrielle.

Usage:
    python scripts/generate_signal.py --fault bpfo --out data/k201_bpfo.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ACQUISITION
from src.diagnostics.bearing import CATALOG, fault_frequencies


def synth_signal(
    fs: float,
    duration_s: float,
    shaft_speed_hz: float,
    fault: str | None = None,
    bearing_name: str = "SKF 6317",
    impact_amplitude: float = 3.0,
    noise_std: float = 0.18,
    resonance_hz: float = 5_000.0,
    damping: float = 900.0,
    seed: int = 42,
) -> np.ndarray:
    """Construit un signal d'acceleration en m/s2.

    Composantes :
      - balourd a fr et harmonique 2fr,
      - bruit de fond gaussien,
      - si `fault` : train d'impacts periodiques a la frequence de defaut,
        chaque impact excitant une resonance structurelle amortie.
    """
    rng = np.random.default_rng(seed)
    n = int(fs * duration_s)
    t = np.arange(n) / fs

    signal = 0.35 * np.sin(2 * np.pi * shaft_speed_hz * t)
    signal += 0.12 * np.sin(2 * np.pi * 2 * shaft_speed_hz * t + 0.7)
    signal += rng.normal(0.0, noise_std, n)

    if fault:
        bearing = CATALOG[bearing_name]
        freqs = fault_frequencies(bearing, shaft_speed_hz)
        f_fault = freqs[fault.upper()]
        period = 1.0 / f_fault

        for k in range(int(duration_s / period)):
            # Glissement aleatoire de 1 % : un defaut reel n'est jamais
            # parfaitement periodique (glissement des elements roulants).
            t0 = k * period * (1 + rng.normal(0, 0.01))
            idx = int(t0 * fs)
            if idx >= n:
                break
            tail = t[idx:] - t[idx]
            burst = (
                impact_amplitude
                * np.exp(-damping * tail)
                * np.sin(2 * np.pi * resonance_hz * tail)
            )
            signal[idx:] += burst

    return signal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fault", choices=["bpfo", "bpfi", "bsf", "ftf"], default=None)
    parser.add_argument("--speed", type=float, default=24.8, help="vitesse d'arbre en Hz")
    parser.add_argument("--duration", type=float, default=2.0, help="duree en secondes")
    parser.add_argument("--bearing", default="SKF 6317")
    parser.add_argument("--out", type=Path, default=Path("data/signal.csv"))
    args = parser.parse_args()

    fs = ACQUISITION.sampling_rate_hz
    signal = synth_signal(
        fs=fs,
        duration_s=args.duration,
        shaft_speed_hz=args.speed,
        fault=args.fault,
        bearing_name=args.bearing,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"time": np.arange(len(signal)) / fs, "acceleration": signal}).to_csv(
        args.out, index=False
    )

    label = args.fault.upper() if args.fault else "sain"
    print(f"{len(signal)} echantillons ({label}, fs={fs:.0f} Hz) -> {args.out}")


if __name__ == "__main__":
    main()
