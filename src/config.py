"""Configuration centralisee, surchargeable par variables d'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class MqttConfig:
    host: str = _env("MQTT_HOST", "localhost")
    port: int = int(_env("MQTT_PORT", "1883"))
    # Convention de topic : <site>/<atelier>/<equipement>/<grandeur>
    topic_pattern: str = _env("MQTT_TOPIC", "site/{site}/{workshop}/{asset}/{measure}")
    qos: int = 1


@dataclass(frozen=True)
class InfluxConfig:
    url: str = _env("INFLUX_URL", "http://localhost:8086")
    token: str = _env("INFLUX_TOKEN", "")
    org: str = _env("INFLUX_ORG", "maintenance")
    bucket: str = _env("INFLUX_BUCKET", "vibrations")


@dataclass(frozen=True)
class AcquisitionConfig:
    # 25,6 kHz : valeur usuelle des collecteurs vibratoires, elle place la
    # frequence de Nyquist (12,8 kHz) au-dessus des bandes de resonance
    # exploitees en analyse d'enveloppe (3-10 kHz).
    sampling_rate_hz: float = 25_600.0
    # Le signal brut n'est PAS publie echantillon par echantillon : il est
    # bufferise en blocs d'une seconde, puis seules les features sont publiees
    # en continu. Le bloc brut n'est remonte qu'a la demande (anomalie detectee).
    window_seconds: float = 1.0
    envelope_band_hz: tuple[float, float] = (3_000.0, 10_000.0)


MQTT = MqttConfig()
INFLUX = InfluxConfig()
ACQUISITION = AcquisitionConfig()
