# -*- coding: cp1256 -*-

import json
import os


BELIEF_FILE = os.path.join(
    "data",
    "beliefs.json"
)


class BeliefSystem:

    def __init__(self):

        self.beliefs = self.load()

    def load(self):

        if not os.path.exists(BELIEF_FILE):
            return {}

        try:

            with open(
                BELIEF_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except:

            return {}

    def save(self):

        with open(
            BELIEF_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.beliefs,
                file,
                ensure_ascii=False,
                indent=2
            )

    def add(
        self,
        subject,
        belief,
        confidence=0.5
    ):

        self.beliefs[subject] = {

            "belief": belief,

            "confidence": confidence

        }

        self.save()

    def get(self, subject):

        return self.beliefs.get(
            subject
        )

    def update(
        self,
        subject,
        new_belief,
        new_confidence
    ):

        old = self.beliefs.get(
            subject
        )

        if old is None:

            self.add(
                subject,
                new_belief,
                new_confidence
            )

            return

        if new_confidence >= old["confidence"]:

            self.beliefs[subject] = {

                "belief": new_belief,

                "confidence": new_confidence

            }

            self.save()