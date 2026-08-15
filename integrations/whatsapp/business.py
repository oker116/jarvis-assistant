import os
import requests


class WhatsAppBusiness:
    def __init__(self):
        self.version = os.getenv(
            "META_GRAPH_API_VERSION",
            "v23.0"
        )
        self.token = os.getenv(
            "META_ACCESS_TOKEN"
        )
        self.phone_number_id = os.getenv(
            "WHATSAPP_PHONE_NUMBER_ID"
        )

    def configured(self):
        return bool(
            self.token and
            self.phone_number_id
        )

    def _url(self):
        return (
            f"https://graph.facebook.com/"
            f"{self.version}/"
            f"{self.phone_number_id}/messages"
        )

    def send_text(self, to, text):
        if not self.configured():
            raise RuntimeError(
                "WhatsApp Cloud API is not configured. "
                "Set META_ACCESS_TOKEN and "
                "WHATSAPP_PHONE_NUMBER_ID."
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": str(to),
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text
            }
        }

        response = requests.post(
            self._url(),
            headers={
                "Authorization": (
                    f"Bearer {self.token}"
                ),
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json()
