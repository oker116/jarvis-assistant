import os
import sys
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
import json
import os
from datetime import datetime

from integrations.sales.lead_analyzer import LeadAnalyzer
from integrations.web.website_analyzer import WebsiteAnalyzer


class LeadManager:

    def __init__(self):

        base_dir = os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        self.data_dir = os.path.join(
            base_dir,
            "data"
        )

        self.file_path = os.path.join(
            self.data_dir,
            "leads.json"
        )

        os.makedirs(
            self.data_dir,
            exist_ok=True
        )

        self.analyzer = LeadAnalyzer()
        self.website_analyzer = WebsiteAnalyzer()

        self.leads = []

        self.load()

    def load(self):

        if not os.path.exists(
            self.file_path
        ):
            return

        try:

            with open(
                self.file_path,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

                if isinstance(data, list):
                    self.leads = data

        except Exception as error:

            print(
                "[LEAD MEMORY ERROR]",
                error
            )

            self.leads = []

    def save(self):

        temp_file = (
            self.file_path
            + ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.leads,
                file,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_file,
            self.file_path
        )

    def create_lead(
        self,
        name,
        website=None,
        facebook=None,
        ads=None,
        has_offer=False,
        has_whatsapp=False
    ):

        lead = {
            "id": self._next_id(),

            "created_at":
                datetime.now().isoformat(),

            "updated_at":
                datetime.now().isoformat(),

            "business": {
                "name": name
            },

            "facebook": facebook or {},

            "ads": ads or {},

            "website": {},

            "has_offer": has_offer,

            "has_whatsapp": has_whatsapp,

            "analysis": {},

            "status": "new"
        }

        # --------------------------------------------------
        # WEBSITE ANALYSIS
        # --------------------------------------------------

        if website:

            print(
                "[LEAD MANAGER] Analyzing website..."
            )

            website_result = (
                self.website_analyzer.analyze(
                    website
                )
            )

            lead["website"] = (
                website_result
            )

        # --------------------------------------------------
        # LEAD ANALYSIS
        # --------------------------------------------------

        lead["analysis"] = (
            self.analyzer.analyze(
                lead
            )
        )

        self.leads.append(
            lead
        )

        self.save()

        return lead

    def get_lead(
        self,
        lead_id
    ):

        for lead in self.leads:

            if lead.get("id") == lead_id:
                return lead

        return None

    def list_leads(
        self,
        minimum_score=0
    ):

        results = []

        for lead in self.leads:

            score = (
                lead
                .get("analysis", {})
                .get("score", 0)
            )

            if score >= minimum_score:
                results.append(
                    lead
                )

        return sorted(
            results,
            key=lambda item:
                item.get(
                    "analysis",
                    {}
                ).get(
                    "score",
                    0
                ),
            reverse=True
        )

    def update_status(
        self,
        lead_id,
        status
    ):

        lead = self.get_lead(
            lead_id
        )

        if not lead:
            return False

        lead["status"] = status

        lead["updated_at"] = (
            datetime.now().isoformat()
        )

        self.save()

        return True

    def _next_id(self):

        if not self.leads:
            return 1

        ids = []

        for lead in self.leads:

            try:
                ids.append(
                    int(
                        lead.get(
                            "id",
                            0
                        )
                    )
                )
            except Exception:
                pass

        return max(ids, default=0) + 1


if __name__ == "__main__":

    manager = LeadManager()

    lead = manager.create_lead(
        name="Example Business",

        website="https://example.com",

        facebook={
            "exists": True,
            "followers": 15000,
            "recent_posts": True
        },

        ads={
            "running": False,
            "historical": False
        },

        has_offer=True,
        has_whatsapp=True
    )

    print()
    print("=" * 60)
    print("JARVIS LEAD")
    print("=" * 60)

    print(
        json.dumps(
            lead,
            ensure_ascii=False,
            indent=2
        )
    )

    print()
    print(
        "Saved to:",
        manager.file_path
    )
