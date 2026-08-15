class AdLibraryAnalyzer:
    """
    Consumes ad-library data obtained from an approved
    Meta source/API and converts it into sales signals.
    """

    def analyze(self, ads):
        ads = ads or []

        active = [
            ad for ad in ads
            if self._is_active(ad)
        ]

        creatives = len(
            self._creative_ids(ads)
        )

        return {
            "total_ads": len(ads),
            "active_ads": len(active),
            "historical_ads": max(
                len(ads) - len(active),
                0
            ),
            "creative_count": creatives,
            "running": bool(active),
            "has_ad_history": bool(ads)
        }

    @staticmethod
    def _is_active(ad):
        if not isinstance(ad, dict):
            return False

        value = ad.get(
            "active",
            ad.get(
                "is_active",
                False
            )
        )

        return bool(value)

    @staticmethod
    def _creative_ids(ads):
        values = set()

        for ad in ads:
            if not isinstance(ad, dict):
                continue

            creative = (
                ad.get("creative_id")
                or ad.get("id")
            )

            if creative:
                values.add(
                    str(creative)
                )

        return values
