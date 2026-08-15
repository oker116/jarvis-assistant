import json
import sqlite3

from integrations.sales.research_to_offer import ResearchToOffer
from integrations.sales.outreach_queue import OutreachQueue


class OutreachOrchestrator:

    def __init__(self):
        self.research = ResearchToOffer()
        self.queue = OutreachQueue()

    def get_candidates(self, limit=50):
        con = sqlite3.connect(
            str(self.research.db_path)
        )
        con.row_factory = sqlite3.Row

        rows = con.execute(
            """
            SELECT lead_id
            FROM leads
            WHERE status NOT IN ('won', 'lost')
              AND lead_id NOT LIKE 'style_test_%'
              AND lead_id NOT LIKE 'test_%'
            ORDER BY score DESC, updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        con.close()

        return [
            row["lead_id"]
            for row in rows
        ]

    def run(self, limit=50):
        results = []

        for lead_id in self.get_candidates(limit):
            try:
                result = self.research.prepare(
                    lead_id
                )

                queued = self.queue.enqueue(
                    result
                )

                results.append({
                    "lead_id": lead_id,
                    "score": result.get("score"),
                    "style": result.get("style"),
                    "send_allowed": result.get(
                        "send_allowed"
                    ),
                    "queued": queued.get(
                        "queued"
                    ),
                    "reason": queued.get(
                        "reason"
                    )
                })

            except Exception as exc:
                results.append({
                    "lead_id": lead_id,
                    "error": str(exc)
                })

        return results


if __name__ == "__main__":
    engine = OutreachOrchestrator()

    results = engine.run()

    print(json.dumps(
        results,
        indent=2,
        ensure_ascii=False
    ))

    print("\n=== QUEUE ===")

    for row in engine.queue.pending():
        print({
            "id": row["id"],
            "lead_id": row["lead_id"],
            "score": row["score"],
            "style": row["style"],
            "status": row["status"]
        })
