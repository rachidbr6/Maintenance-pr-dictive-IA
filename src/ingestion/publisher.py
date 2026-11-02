"""Publication MQTT des features vibratoires depuis la passerelle edge.

Point d'architecture important : on ne publie PAS les echantillons bruts
(25 600 valeurs/s/capteur saturerait le broker et le reseau atelier). La
passerelle bufferise le signal par fenetres d'une seconde, calcule les features
localement, et ne publie que celles-ci. Le bloc brut n'est remonte qu'a la
demande, quand une anomalie est confirmee et qu'un diagnostic fin est requis.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np
import paho.mqtt.client as mqtt

from src.config import ACQUISITION, MQTT
from src.diagnostics.bearing import CATALOG
from src.features.vibration import extract_features


def build_topic(site: str, workshop: str, asset: str, measure: str) -> str:
    return MQTT.topic_pattern.format(site=site, workshop=workshop, asset=asset, measure=measure)


def publish_window(
    client: mqtt.Client,
    signal: np.ndarray,
    *,
    site: str,
    workshop: str,
    asset: str,
    bearing_name: str,
    shaft_speed_hz: float,
    bearing_temperature_c: float | None = None,
) -> dict:
    """Calcule les features d'une fenetre et les publie sur le broker."""
    bearing = CATALOG[bearing_name]
    payload = extract_features(signal, ACQUISITION.sampling_rate_hz, bearing, shaft_speed_hz)

    payload.update(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "asset": asset,
            "bearing": bearing_name,
            "shaft_speed_hz": shaft_speed_hz,
        }
    )
    if bearing_temperature_c is not None:
        payload["temperature"] = bearing_temperature_c

    topic = build_topic(site, workshop, asset, "vibration_features")
    client.publish(topic, json.dumps(payload), qos=MQTT.qos)
    return payload


def connect() -> mqtt.Client:
    client = mqtt.Client()
    client.connect(MQTT.host, MQTT.port, keepalive=60)
    client.loop_start()
    return client


if __name__ == "__main__":
    from scripts.generate_signal import synth_signal

    fs = ACQUISITION.sampling_rate_hz
    client = connect()
    print(f"publication sur {MQTT.host}:{MQTT.port} -- Ctrl+C pour arreter")

    try:
        while True:
            window = synth_signal(fs=fs, duration_s=1.0, shaft_speed_hz=24.8, seed=int(time.time()))
            sent = publish_window(
                client,
                window,
                site="pilote",
                workshop="preparation",
                asset="K201",
                bearing_name="SKF 6317",
                shaft_speed_hz=24.8,
                bearing_temperature_c=52.4,
            )
            print(f"{sent['timestamp']}  rms={sent['rms']:.3f}  kurt={sent['kurtosis']:.2f}")
            time.sleep(ACQUISITION.window_seconds)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
