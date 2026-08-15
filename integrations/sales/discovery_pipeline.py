import json
import sys

from integrations.sales.meta_discovery import discover
from integrations.sales.lead_discovery import LeadDiscovery
from integrations.sales.outreach_orchestrator import OutreachOrchestrator


def build_lead(item):
    fb = item.get("facebook", {})
    website = item.get("website", {})
    ads = item.get("ads", {})

    return {
        "lead_id": fb.get("url", item.get("name", "unknown")),
        "name": item.get("name") or "Unknown",
        "source": "facebook_discovery",
        "facebook": fb,
        "instagram": {},
        "ads": ads,
        "website": website,
        "has_offer": False,
        "has_whatsapp": bool(
            website.get("contact", {}).get("whatsapp")
        ),
    }


def run(query, limit=5):
    raw = discover(query, limit)

    leads = [
        build_lead(item)
        for item in raw
    ]

    ingester = LeadDiscovery()
    created = ingester.ingest(leads)

    orchestrator = OutreachOrchestrator()
    results = orchestrator.run(limit=len(created))

    return {
        "query": query,
        "discovered": len(raw),
        "ingested": created,
        "pipeline": results,
    }


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]).strip()

    if not query:
        raise SystemExit(
            'Usage: python3 -m integrations.sales.discovery_pipeline '
            '"restaurant Cairo"'
        )

    print(json.dumps(
        run(query),
        indent=2,
        ensure_ascii=False
    ))
