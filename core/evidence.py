# -*- coding: cp1256 -*-

import json
import os
from datetime import datetime


EVIDENCE_FILE = os.path.join(
    "data",
    "evidence.json"
)


class EvidenceEngine:

    def __init__(self):
        self.evidence = self.load()

    def load(self):

        if not os.path.exists(EVIDENCE_FILE):
            return []

        try:

            with open(
                EVIDENCE_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except:

            return []

    def save(self):

        with open(
            EVIDENCE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.evidence,
                file,
                ensure_ascii=False,
                indent=2
            )

    def add(
        self,
        subject,
        claim,
        source,
        reliability=0.5
    ):

        item = {
            "subject": subject,
            "claim": claim,
            "source": source,
            "reliability": reliability,
            "time": datetime.now().isoformat()
        }

        self.evidence.append(item)

        self.save()

        return item

    def get_for_subject(self, subject):

        results = []

        for item in self.evidence:

            if item["subject"].lower() == subject.lower():

                results.append(item)

        return results

    def evaluate(self, subject):

        items = self.get_for_subject(subject)

        if not items:
            return {
                "subject": subject,
                "status": "no_evidence",
                "confidence": 0.0,
                "best_claim": None
            }

        best = max(
            items,
            key=lambda x: x["reliability"]
        )

        return {
            "subject": subject,
            "status": "evidence_found",
            "confidence": best["reliability"],
            "best_claim": best["claim"],
            "source": best["source"]
        }