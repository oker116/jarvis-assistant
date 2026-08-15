class MetaSalesSignals:
    """
    Converts normalized Facebook/Instagram + Ad Library
    data into practical sales signals.
    """

    def build(self, profile):
        ads = profile.ads or {}
        facebook = profile.facebook or {}
        instagram = profile.instagram or {}

        signals = {
            "has_whatsapp": bool(
                profile.whatsapp
            ),
            "has_website": bool(
                profile.website
            ),
            "facebook_active": bool(
                facebook.get(
                    "recent_posts"
                )
            ),
            "instagram_active": bool(
                instagram.get(
                    "recent_posts"
                )
            ),
            "running_ads": bool(
                ads.get("running")
            ),
            "ad_history": bool(
                ads.get("has_ad_history")
            ),
            "creative_count": int(
                ads.get(
                    "creative_count",
                    0
                ) or 0
            )
        }

        score = 0

        if signals["has_whatsapp"]:
            score += 20

        if signals["has_website"]:
            score += 10

        if signals["facebook_active"]:
            score += 10

        if signals["instagram_active"]:
            score += 10

        if signals["running_ads"]:
            score += 25

        if signals["ad_history"]:
            score += 10

        if signals["creative_count"] >= 3:
            score += 5

        if score >= 70:
            priority = "high"
        elif score >= 45:
            priority = "medium"
        else:
            priority = "low"

        return {
            "signals": signals,
            "score": score,
            "priority": priority
        }
