"""Diagnostic vibratoire bout-en-bout sur un signal CSV.

Chaine : chargement -> indicateurs temporels -> spectre d'enveloppe ->
correspondance avec les frequences de defaut -> severite ISO 20816-3.

Usage:
    python scripts/diagnose.py data/k201_bpfo.csv --speed 24.8 --bearing "SKF 6317"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ACQUISITION
from src.diagnostics.bearing import CATALOG, fault_frequencies, fault_orders, iso_zone, match_peak
from src.features.vibration import envelope_spectrum, time_domain_features, top_peaks


def velocity_rms_mm_s(acceleration: np.ndarray, fs: float) -> float:
    """Vitesse vibratoire efficace en mm/s, bande 10-1000 Hz (ISO 20816-3).

    Integration realisee dans le domaine frequentiel : v(f) = a(f) / (2*pi*f),
    plus stable numeriquement qu'une integration temporelle qui derive.
    """
    x = np.asarray(acceleration, dtype=float)
    x = x - x.mean()
    spec = np.abs(np.fft.rfft(x)) * 2 / len(x)
    freqs = np.fft.rfftfreq(len(x), d=1 / fs)

    band = (freqs >= 10.0) & (freqs <= 1000.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        velocity = np.where(band, spec / (2 * np.pi * np.maximum(freqs, 1e-9)), 0.0)

    # m/s -> mm/s, puis RMS a partir des amplitudes crete du spectre.
    return float(np.sqrt(np.sum((velocity * 1000.0) ** 2) / 2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("signal", type=Path, help="CSV avec une colonne 'acceleration'")
    parser.add_argument("--speed", type=float, required=True, help="vitesse d'arbre mesuree en Hz")
    parser.add_argument("--bearing", default="SKF 6317")
    parser.add_argument("--fs", type=float, default=ACQUISITION.sampling_rate_hz)
    args = parser.parse_args()

    df = pd.read_csv(args.signal)
    signal = df["acceleration"].to_numpy()
    bearing = CATALOG[args.bearing]

    stats = time_domain_features(signal)
    v_rms = velocity_rms_mm_s(signal, args.fs)
    zone, advice = iso_zone(v_rms)

    print(f"\nSignal      : {args.signal}  ({len(signal)} pts @ {args.fs:.0f} Hz)")
    print(f"Roulement   : {bearing.name}  (Z={bearing.n_balls}, d/D={bearing.ratio:.4f})")
    print(f"Vitesse     : {args.speed:.2f} Hz  ({args.speed * 60:.0f} tr/min)")

    print("\n--- Indicateurs temporels ---")
    for key, value in stats.items():
        print(f"  {key:<14} {value:>8.3f}")
    print(f"  {'v_rms (mm/s)':<14} {v_rms:>8.3f}   -> zone {zone} : {advice}")

    print("\n--- Frequences de defaut attendues ---")
    orders = fault_orders(bearing)
    for name, value in fault_frequencies(bearing, args.speed).items():
        print(f"  {name:<6} {value:>8.2f} Hz   (ordre {orders[name]:.3f} x fr)")

    print("\n--- Pics du spectre d'enveloppe ---")
    freqs, amps = envelope_spectrum(signal, args.fs, ACQUISITION.envelope_band_hz)
    for peak_hz, amplitude in top_peaks(freqs, amps, n=6):
        hit = match_peak(peak_hz, bearing, args.speed)
        tag = (
            f"-> {hit[0]} x{hit[1]} (ecart {hit[2] * 100:.2f} %)"
            if hit
            else "-> non attribue"
        )
        print(f"  {peak_hz:>8.2f} Hz   amp={amplitude:.4f}   {tag}")

    if stats["kurtosis"] > 6:
        print("\n[!] Kurtosis > 6 : impacts transitoires -- coherent avec un ecaillage naissant.")
    print()


if __name__ == "__main__":
    main()
