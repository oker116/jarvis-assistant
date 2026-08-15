import json
import re


class LeadAnalyzer:

    def __init__(self):
        self.version = "1.0"

    def analyze(self, lead):
        """
        Analyze a business as a potential Media Buying client.

        The analyzer distinguishes between:
        - observed facts
        - signals
        - recommendations
        """

        score = 0
        signals = []
        opportunities = []

        page = lead.get("facebook", {})
        ads = lead.get("ads", {})
        website = lead.get("website", {})

        # --------------------------------------------------
        # FACEBOOK PRESENCE
        # --------------------------------------------------

        if page.get("exists"):
            score += 10
            signals.append(
                "Active Facebook presence detected."
            )

        followers = self._number(
            page.get("followers")
        )

        if followers:

            if followers >= 100000:
                score += 10
                signals.append(
                    "Large Facebook audience."
                )

            elif followers >= 10000:
                score += 7
                signals.append(
                    "Established Facebook audience."
                )

            elif followers >= 1000:
                score += 4
                signals.append(
                    "Growing Facebook audience."
                )

        posts_recent = page.get(
            "recent_posts"
        )

        if posts_recent:
            score += 5
            signals.append(
                "Recent Facebook activity detected."
            )

        # --------------------------------------------------
        # PAID ADS
        # --------------------------------------------------

        if ads.get("running"):
            score += 20
            signals.append(
                "Active paid advertising detected."
            )

            opportunities.append(
                "Campaign optimization opportunity."
            )

        elif ads.get("historical"):
            score += 8
            signals.append(
                "Historical advertising activity detected."
            )

            opportunities.append(
                "Potential opportunity to restart or improve paid campaigns."
            )

        else:
            opportunities.append(
                "No advertising activity was confirmed from supplied data."
            )

        creative_count = self._number(
            ads.get("creative_count")
        )

        if creative_count:

            if creative_count <= 2:
                score += 7
                signals.append(
                    "Limited creative variation."
                )

                opportunities.append(
                    "Creative testing opportunity."
                )

            elif creative_count >= 5:
                score += 4
                signals.append(
                    "Multiple advertising creatives detected."
                )

        # --------------------------------------------------
        # WEBSITE
        # --------------------------------------------------

        if website.get("exists"):

            score += 10
            signals.append(
                "Business website detected."
            )

            if website.get("has_cta"):
                score += 5
                signals.append(
                    "Website has a visible conversion CTA."
                )
            else:
                opportunities.append(
                    "Website CTA optimization opportunity."
                )

            if website.get("has_tracking"):
                score += 5
                signals.append(
                    "Tracking technology detected."
                )
            else:
                opportunities.append(
                    "Tracking setup should be reviewed."
                )

            if website.get("landing_page"):
                score += 5
                signals.append(
                    "Dedicated landing page detected."
                )
            else:
                opportunities.append(
                    "Landing page optimization opportunity."
                )

        # --------------------------------------------------
        # COMMERCIAL SIGNALS
        # --------------------------------------------------

        if lead.get("has_offer"):
            score += 5
            signals.append(
                "Commercial offer detected."
            )

        if lead.get("has_whatsapp"):
            score += 5
            signals.append(
                "Business WhatsApp contact detected."
            )

        # --------------------------------------------------
        # SCORE NORMALIZATION
        # --------------------------------------------------

        score = min(
            max(score, 0),
            100
        )

        if score >= 80:
            priority = "HIGH"

        elif score >= 60:
            priority = "MEDIUM"

        elif score >= 40:
            priority = "LOW"

        else:
            priority = "VERY_LOW"

        # --------------------------------------------------
        # RESULT
        # --------------------------------------------------

        return {
            "score": score,
            "priority": priority,
            "signals": signals,
            "opportunities": opportunities,
            "recommended_service": self._recommend_service(
                score,
                opportunities
            ),
            "analyzer_version": self.version
        }

    def _recommend_service(
        self,
        score,
        opportunities
    ):

        if score >= 80:

            return (
                "Media Buying + Campaign Optimization "
                "+ Creative Testing"
            )

        if score >= 60:

            return (
                "Media Buying Audit + Campaign Optimization"
            )

        if score >= 40:

            return (
                "Paid Advertising Audit"
            )

        return (
            "Nurture lead / collect more information"
        )

    @staticmethod
    def _number(value):

        if value is None:
            return None

        if isinstance(value, (int, float)):
            return int(value)

        value = str(value)

        value = re.sub(
            r"[^\d]",
            "",
            value
        )

        if not value:
            return None

        try:
            return int(value)
        except ValueError:
            return None


if __name__ == "__main__":

    analyzer = LeadAnalyzer()

    example = {
        "facebook": {
            "exists": True,
            "followers": 18500,
            "recent_posts": True
        },

        "ads": {
            "running": True,
            "historical": True,
            "creative_count": 2
        },

        "website": {
            "exists": True,
            "has_cta": True,
            "has_tracking": False,
            "landing_page": False
        },

        "has_offer": True,
        "has_whatsapp": True
    }

    result = analyzer.analyze(
        example
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )
