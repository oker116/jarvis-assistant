import re
from urllib.parse import urlparse

from integrations.meta.lead_profile import (
    MetaLeadProfile
)


class MetaLeadDiscovery:
    """
    Normalizes Facebook / Instagram leads.

    Discovery itself should be supplied by an approved
    Meta data source/API. This module deliberately does
    not scrape Facebook or Instagram.
    """

    WHATSAPP_PATTERNS = (
        r"wa\.me/",
        r"api\.whatsapp\.com/",
        r"whatsapp\.com/"
    )

    def normalize(self, raw):
        if not isinstance(raw, dict):
            raise TypeError(
                "raw lead must be a dict"
            )

        platform = raw.get(
            "platform",
            "facebook"
        )

        profile_url = raw.get(
            "profile_url",
            ""
        )

        website = raw.get(
            "website"
        )

        whatsapp = self._find_whatsapp(
            raw
        )

        profile = MetaLeadProfile(
            platform=platform,
            profile_url=profile_url,
            business_name=raw.get(
                "business_name",
                ""
            ),
            category=raw.get(
                "category",
                ""
            ),
            whatsapp=whatsapp,
            website=website,
            facebook=raw.get(
                "facebook",
                {}
            ),
            instagram=raw.get(
                "instagram",
                {}
            ),
            ads=raw.get(
                "ads",
                {}
            ),
            website_analysis=raw.get(
                "website_analysis",
                {}
            )
        )

        return profile

    def qualify_contact(self, profile):
        return bool(
            profile.whatsapp
        )

    def _find_whatsapp(self, raw):
        candidates = []

        for key in (
            "whatsapp",
            "phone",
            "contact",
            "website"
        ):
            value = raw.get(key)

            if isinstance(value, str):
                candidates.append(value)

        for section in (
            "facebook",
            "instagram",
            "website_analysis"
        ):
            value = raw.get(section)

            if isinstance(value, dict):
                candidates.extend(
                    self._flatten_strings(value)
                )

        for value in candidates:
            if self._is_whatsapp(value):
                return value

        return None

    def _flatten_strings(self, value):
        result = []

        if isinstance(value, dict):
            for item in value.values():
                result.extend(
                    self._flatten_strings(item)
                )

        elif isinstance(value, list):
            for item in value:
                result.extend(
                    self._flatten_strings(item)
                )

        elif isinstance(value, str):
            result.append(value)

        return result

    def _is_whatsapp(self, value):
        return any(
            re.search(
                pattern,
                value,
                re.IGNORECASE
            )
            for pattern in self.WHATSAPP_PATTERNS
        )

    @staticmethod
    def valid_meta_profile(url):
        if not url:
            return False

        parsed = urlparse(url)

        host = (
            parsed.netloc
            .lower()
            .replace(
                "www.",
                ""
            )
        )

        return host in {
            "facebook.com",
            "instagram.com"
        }
