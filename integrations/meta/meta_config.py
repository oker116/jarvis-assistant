import os


class MetaConfig:
    GRAPH_API_VERSION = os.getenv(
        "META_GRAPH_API_VERSION",
        "v23.0"
    )

    ACCESS_TOKEN = os.getenv(
        "META_ACCESS_TOKEN"
    )

    APP_ID = os.getenv(
        "META_APP_ID"
    )

    APP_SECRET = os.getenv(
        "META_APP_SECRET"
    )

    @classmethod
    def validate(cls):
        if not cls.ACCESS_TOKEN:
            raise RuntimeError(
                "META_ACCESS_TOKEN is missing"
            )

        return True
