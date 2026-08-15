import json
import sqlite3
from pathlib import Path

from integrations.sales.lead_analyzer import LeadAnalyzer
from integrations.sales.personalized_offer import PersonalizedOfferGenerator


class ResearchToOffer:
    """
    Research -> Lead Analysis -> Egyptian personalized outreach.

    OUTREACH ONLY:
    This module prepares an offer.
    It does NOT send messages.
    It does NOT auto-reply.
    """

    def __init__(self, db_path=None):
        root = Path(__file__).resolve().parents[2]

        self.db_path = Path(
            db_path or root / "data" / "sales.db"
        )

        self.analyzer = LeadAnalyzer()
        self.offer_generator = PersonalizedOfferGenerator()

    def get_lead(self, lead_id):
        con = sqlite3.connect(str(self.db_path))
        con.row_factory = sqlite3.Row

        row = con.execute(
            """
            SELECT
                lead_id,
                name,
                source,
                status,
                score,
                priority,
                metadata_json
            FROM leads
            WHERE lead_id = ?
            """,
            (lead_id,)
        ).fetchone()

        con.close()

        if not row:
            return None

        lead = dict(row)

        try:
            metadata = json.loads(
                lead.get("metadata_json") or "{}"
            )
        except Exception:
            metadata = {}

        # IMPORTANT:
        # LeadAnalyzer expects research fields at the top level.
        # The DB stores them inside metadata_json.
        for key, value in metadata.items():
            lead[key] = value

        lead["metadata"] = metadata

        # Normalize common website fields.
        website = lead.get("website") or {}

        # "success" is how the current researcher records
        # that a real website was successfully inspected.
        if "exists" not in website:
            website["exists"] = bool(
                website.get("success")
                or website.get("url")
                or website.get("domain")
            )

        lead["website"] = website

        if "has_cta" not in lead:
            lead["has_cta"] = bool(
                website.get("cta", {}).get("detected")
                or website.get("has_cta")
            )

        if "has_tracking" not in lead:
            tracking = website.get("tracking") or {}
            lead["has_tracking"] = bool(
                website.get("has_tracking")
                or tracking.get("detected")
                or any(
                    tracking.get(k)
                    for k in [
                        "facebook_pixel",
                        "google_analytics",
                        "google_tag_manager",
                        "tiktok_pixel",
                        "snap_pixel",
                        "linkedin_insight",
                    ]
                )
            )

        if "landing_page" not in lead:
            lead["landing_page"] = bool(
                website.get("landing_page")
            )

        # Normalize WhatsApp/contact signals.
        contact = website.get("contact") or {}

        if "has_whatsapp" not in lead:
            lead["has_whatsapp"] = bool(
                lead.get("has_whatsapp")
                or contact.get("whatsapp")
            )

        # Commercial signals.
        commercial = website.get(
            "commercial_signals"
        ) or {}

        if "has_offer" not in lead:
            lead["has_offer"] = bool(
                lead.get("has_offer")
                or commercial.get("has_offer_language")
                or commercial.get("has_pricing")
            )

        return lead

    def prepare(self, lead_id, style=None):
        lead = self.get_lead(lead_id)

        if not lead:
            raise ValueError(
                f"Lead not found: {lead_id}"
            )

        # Analyze the actual research.
        analysis = self.analyzer.analyze(lead)

        research = {
            "findings": analysis.get("signals", []),
            "opportunities": analysis.get(
                "opportunities", []
            ),
            "raw": lead.get("metadata", {}),
        }

        result = self.offer_generator.generate(
            lead=lead,
            analysis=analysis,
            research=research,
            style=style,
        )

        # Record which style was prepared.
        # This does NOT send the message.
        try:
            from integrations.sales.conversation_learning import (
                ConversationLearning
            )

            learning = ConversationLearning(
                db_path=self.db_path
            )

            learning.record_offer_style(
                lead_id=lead["lead_id"],
                style=result.get("style", "unknown"),
                service=result.get("service"),
                score=result.get("score"),
            )

        except Exception:
            # Learning must never break outreach preparation.
            pass

        # Never send automatically.
        result["research_used"] = True
        result["auto_reply"] = False
        result["mode"] = "OUTREACH_ONLY"

        # Conservative qualification gate.
        result["send_allowed"] = bool(
            result.get("score", 0) >= 60
            and lead.get("status")
            not in {"won", "lost"}
            and len(result.get("evidence", [])) >= 1
        )

        return result


if __name__ == "__main__":
    import sys

    engine = ResearchToOffer()

    lead_id = sys.argv[1] if len(sys.argv) > 1 else "2"

    result = engine.prepare(lead_id)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )
