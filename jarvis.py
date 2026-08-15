# -*- coding: cp1256 -*-

import json
import os
from datetime import datetime


MEMORY_FILE = os.path.join("data", "memory.json")


class Jarvis:

    def __init__(self):

        self.name = "JARVIS"
        self.user_name = "P.C"

        self.state = "IDLE"

        self.memory = self.load_memory()

    def load_memory(self):

        if not os.path.exists(MEMORY_FILE):
            return []

        try:

            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except:

            return []

    def save_memory(self):

        if not os.path.exists("data"):
            os.makedirs("data")

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.memory,
                file,
                ensure_ascii=False,
                indent=2
            )

    def remember(self, text):

        item = {
            "time": datetime.now().isoformat(),
            "text": text
        }

        self.memory.append(item)

        self.save_memory()

    def analyze_state(self, message):

        text = message.lower()

        if (
            "حلل" in text
            or "فكر" in text
            or "تحليل" in text
        ):

            self.state = "THINKING"

        elif (
            "تعلم" in text
            or "احفظ" in text
            or "معلومة" in text
        ):

            self.state = "LEARNING"

        elif (
            "نفذ" in text
            or "افتح" in text
            or "شغل" in text
        ):

            self.state = "ACTIVE"

        else:

            self.state = "IDLE"

        return self.state

    def think(self, message):

        message = message.strip()

        if not message:

            return "لم تقل شيئًا."

        state = self.analyze_state(message)

        if message.startswith("تذكر:"):

            information = message.replace(
                "تذكر:",
                "",
                1
            ).strip()

            if information:

                self.remember(
                    information
                )

                self.state = "LEARNING"

                return (
                    "تم حفظ المعلومة."
                )

        if message == "ذاكرتي":

            if not self.memory:

                return (
                    "ذاكرتي فارغة."
                )

            result = (
                "المعلومات التي أتذكرها:\n"
            )

            for item in self.memory:

                result += (
                    "- "
                    + item["text"]
                    + "\n"
                )

            return result

        if state == "THINKING":

            return (
                "أقوم بتحليل الطلب..."
            )

        if state == "LEARNING":

            return (
                "أستعد لتعلم المعلومات..."
            )

        if state == "ACTIVE":

            return (
                "أستعد لتنفيذ الأمر..."
            )

        return (
            "استلمت طلبك."
        )


def main():

    jarvis = Jarvis()

    print("=" * 50)
    print("JARVIS CORE")
    print("Personal AI System")
    print("=" * 50)

    print(
        "اكتب خروج لإنهاء البرنامج."
    )

    print()

    while True:

        user = input("أنت > ")

        if user.strip() in [
            "خروج",
            "exit",
            "quit"
        ]:

            break

        response = jarvis.think(
            user
        )

        print(
            "JARVIS >",
            response
        )

        print(
            "STATE >",
            jarvis.state
        )

        print()


if __name__ == "__main__":

    main()