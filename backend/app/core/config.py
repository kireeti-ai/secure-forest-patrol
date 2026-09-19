"""Forest backend configuration.

The forest backend has NO authentication layer, so there is no secret key,
no JWT signing material and no gateway shared secret to configure. The only
secret-adjacent value is ``DATABASE_URL``.

Environment variables::

    DATABASE_URL            required, PostgreSQL connection string
    FOREST_ENVIRONMENT      default "development"
    FOREST_CORS_ORIGINS     optional comma-separated allowlist
    ACCESS_TOKEN_EXPIRE_MINUTES  unused, retained for compatibility
    MQTT_BROKER_HOST        default "localhost"
    MQTT_BROKER_PORT        default "1883"
    MQTT_USERNAME           optional
    MQTT_PASSWORD           optional
    MQTT_TLS                optional, "true"/"1" enables TLS
"""

import os
from pathlib import Path


def _load_env_file() -> None:
    for filename in [".env", "backend.env"]:
        env_path = Path(__file__).resolve().parent.parent.parent / filename
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key not in os.environ:
                            os.environ[key] = val


_load_env_file()


def _getenv(*names: str, default: str | None = None) -> str | None:
    """Read the first set variable in ``names`` order.

    The forest backend reads forest-scoped names only. There is no legacy
    maritime configuration namespace.
    """
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


def get_database_url() -> str:
    database_url = _getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set before database access or migrations")
    return database_url


def get_environment() -> str:
    return _getenv("FOREST_ENVIRONMENT", default="development") or "development"


def get_cors_origins() -> list[str]:
    configured = _getenv("FOREST_CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    if get_environment() == "development":
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    # The deployed dashboard and API share the production Vercel origin.
    # Operators can override this with FOREST_CORS_ORIGINS for a custom domain.
    return ["https://secure-forest-patrol-4cxw.vercel.app"]


class MqttConfig:
    def __init__(self) -> None:
        self.host = _getenv("MQTT_BROKER_HOST", default="localhost")
        self.port = int(_getenv("MQTT_BROKER_PORT", default="1883") or "1883")
        self.username = _getenv("MQTT_USERNAME")
        self.password = _getenv("MQTT_PASSWORD")
        self.tls = (_getenv("MQTT_TLS", default="false") or "false").lower() in ("1", "true", "yes")


def get_mqtt_config() -> MqttConfig:
    return MqttConfig()
