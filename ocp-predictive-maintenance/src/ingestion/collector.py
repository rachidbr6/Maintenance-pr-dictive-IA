"""Abonne MQTT -> ecriture InfluxDB -> scoring Isolation Forest.

Ce collecteur constitue le pont entre la couche transport et la couche
analytique : il persiste chaque fenetre de features et declenche une alerte
des qu'une anomalie est detectee.
"""

from __future__ import annotations

import json
from typing import Callable

import pandas as pd
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

from src.anomaly.detector import AnomalyDetector
from src.config import INFLUX, MQTT
from src.features.vibration import FEATURE_NAMES

FLUX_FEATURES = """
from(bucket: "{bucket}")
  |> range(start: -{lookback})
  |> filter(fn: (r) => r._measurement == "vibration_features")
  |> filter(fn: (r) => r.asset == "{asset}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
"""


def load_features(client: InfluxDBClient, asset: str, lookback: str = "1h") -> pd.DataFrame:
    """Recharge l'historique des features d'un equipement depuis InfluxDB."""
    query = FLUX_FEATURES.format(bucket=INFLUX.bucket, asset=asset, lookback=lookback)
    df = client.query_api().query_data_frame(query, org=INFLUX.org)
    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)
    return df


def to_point(payload: dict) -> Point:
    point = (
        Point("vibration_features")
        .tag("asset", payload["asset"])
        .tag("bearing", payload.get("bearing", "unknown"))
        .time(payload["timestamp"], WritePrecision.MS)
    )
    for field in FEATURE_NAMES + ["temperature", "shaft_speed_hz"]:
        if field in payload:
            point = point.field(field, float(payload[field]))
    return point


def run(detector: AnomalyDetector, on_anomaly: Callable[[dict], None] | None = None) -> None:
    """Boucle principale : consomme les messages, persiste, score, alerte."""
    influx = InfluxDBClient(url=INFLUX.url, token=INFLUX.token, org=INFLUX.org)
    write_api = influx.write_api(write_options=SYNCHRONOUS)

    def on_message(_client, _userdata, message) -> None:
        payload = json.loads(message.payload.decode())
        write_api.write(bucket=INFLUX.bucket, org=INFLUX.org, record=to_point(payload))

        scored = detector.score(pd.DataFrame([payload])).iloc[0]
        if scored["is_anomaly"]:
            alert = {
                "asset": payload["asset"],
                "timestamp": payload["timestamp"],
                "anomaly_score": float(scored["anomaly_score"]),
                "kurtosis": payload["kurtosis"],
                "rms": payload["rms"],
            }
            print(f"[ALERTE] {alert}")
            if on_anomaly:
                on_anomaly(alert)

    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT.host, MQTT.port, keepalive=60)
    client.subscribe("site/+/+/+/vibration_features", qos=MQTT.qos)
    client.loop_forever()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit("usage: python -m src.ingestion.collector <chemin_modele.joblib>")
    run(AnomalyDetector.load(sys.argv[1]))
