from integrations.sales.lead_manager import LeadManager
from integrations.sales.sales_memory import SalesMemory
from integrations.sales.learning_engine import SalesLearningEngine
from integrations.sales.offer_generator import OfferGenerator


class SalesAgent:

    def __init__(self):
        self.leads = LeadManager()
        self.memory = SalesMemory()
        self.learning = SalesLearningEngine(self.memory)
        self.offer_generator = OfferGenerator()

    def create_lead(
        self,
        name,
        website=None,
        facebook=None,
        instagram=None,
        ads=None,
        has_offer=False,
        has_whatsapp=False
    ):
        lead = self.leads.create_lead(
            name=name,
            website=website,
            facebook=facebook,
            ads=ads,
            has_offer=has_offer,
            has_whatsapp=has_whatsapp
        )

        lead["instagram"] = instagram or {}

        lead["analysis"]["source"] = "meta"

        lead_id = str(lead["id"])

        analysis = lead.get("analysis", {})

        self.memory.upsert_lead(
            lead_id=lead_id,
            name=name,
            source="facebook_instagram",
            status=lead.get("status", "new"),
            score=analysis.get("score", 0),
            priority=analysis.get("priority"),
            metadata={
                "facebook": facebook or {},
                "instagram": instagram or {},
                "ads": ads or {},
                "website": lead.get("website", {})
            }
        )

        features = self.extract_features(lead)

        self.memory.record_event(
            lead_id=lead_id,
            event_type="lead_discovered",
            channel="meta",
            metadata={
                "features": features
            }
        )

        self.memory.record_event(
            lead_id=lead_id,
            event_type="lead_analyzed",
            channel="meta",
            metadata={
                "score": analysis.get("score", 0),
                "priority": analysis.get("priority"),
                "features": features
            }
        )

        return lead

    def generate_offer(self, lead_id):
        lead = self.leads.get_lead(lead_id)

        if not lead:
            raise ValueError(
                f"Lead {lead_id} not found"
            )

        result = self.offer_generator.generate(
            lead
        )

        self.memory.record_event(
            lead_id=str(lead_id),
            event_type="offer_generated",
            channel="sales",
            content=result["message"],
            metadata={
                "signals": result["signals"],
                "problems": result["problems"]
            }
        )

        return result

    def record_chat(
        self,
        lead_id,
        message,
        direction="inbound",
        channel="whatsapp",
        metadata=None
    ):
        self.memory.record_event(
            lead_id=str(lead_id),
            event_type=(
                "message_received"
                if direction == "inbound"
                else "message_sent"
            ),
            channel=channel,
            actor=(
                "customer"
                if direction == "inbound"
                else "jarvis"
            ),
            content=message,
            metadata=metadata or {}
        )

    def record_outcome(
        self,
        lead_id,
        outcome,
        revenue=0,
        reason=None
    ):
        lead = self.leads.get_lead(lead_id)

        features = (
            self.extract_features(lead)
            if lead
            else {}
        )

        self.memory.record_outcome(
            lead_id=str(lead_id),
            outcome=outcome,
            revenue=revenue,
            reason=reason,
            metadata={
                "features": features
            }
        )

        self.memory.record_event(
            lead_id=str(lead_id),
            event_type="sales_outcome",
            metadata={
                "outcome": outcome,
                "revenue": revenue,
                "reason": reason,
                "features": features
            }
        )

        return self.learning.rebuild()

    @staticmethod
    def extract_features(lead):
        if not lead:
            return {}

        business = lead.get("business", {})
        facebook = lead.get("facebook", {})
        instagram = lead.get("instagram", {})
        ads = lead.get("ads", {})
        website = lead.get("website", {})
        contact = website.get("contact", {})
        cta = website.get("cta", {})
        tracking = website.get("tracking", {})

        return {
            "industry": business.get(
                "category",
                "unknown"
            ),
            "facebook_active": bool(
                facebook.get("recent_posts")
            ),
            "instagram_active": bool(
                instagram.get("recent_posts")
            ),
            "ads_running": bool(
                ads.get("running")
            ),
            "ad_history": bool(
                ads.get("historical")
            ),
            "creative_count": int(
                ads.get("creative_count", 0) or 0
            ),
            "website_exists": bool(
                website.get("success")
                or website
            ),
            "website_cta": bool(
                cta.get("detected")
            ),
            "website_whatsapp": bool(
                contact.get("whatsapp")
            ),
            "tracking_detected": bool(
                tracking.get("detected")
            ),
            "has_offer": bool(
                lead.get("has_offer")
            ),
            "has_whatsapp": bool(
                lead.get("has_whatsapp")
                or contact.get("whatsapp")
            )
        }


if __name__ == "__main__":
    agent = SalesAgent()

    lead = agent.create_lead(
        name="Test Restaurant",
        website="https://example.com",
        facebook={
            "exists": True,
            "recent_posts": True
        },
        instagram={
            "exists": True,
            "recent_posts": True
        },
        ads={
            "running": True,
            "historical": True,
            "creative_count": 4
        },
        has_offer=False,
        has_whatsapp=True
    )

    print("Lead:", lead["id"])
    print("Score:", lead["analysis"].get("score"))

    offer = agent.generate_offer(
        lead["id"]
    )

    print("\n===== SALES MESSAGE =====\n")
    print(offer["message"])
