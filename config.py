import json
import os

ARCHIVO_CONFIG = "config.json"


def cargar_config():

    if not os.path.exists(ARCHIVO_CONFIG):
        raise FileNotFoundError(
            f"No existe {ARCHIVO_CONFIG}"
        )

    with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_config(config):

    with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(
            config,
            f,
            indent=4,
            ensure_ascii=False
        )


CONFIG = cargar_config()