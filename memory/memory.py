import os
import json
import threading
import re


class JarvisMemory:

    def __init__(self):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        self.data_dir = os.path.join(base_dir, "data")
        self.file_path = os.path.join(
            self.data_dir,
            "memory.json"
        )

        os.makedirs(self.data_dir, exist_ok=True)

        self.lock = threading.Lock()

        self.data = {
            "profile": {},
            "memories": [],
            "conversations": []
        }

        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        try:
            with open(
                self.file_path,
                "r",
                encoding="utf-8"
            ) as f:
                loaded = json.load(f)

            if isinstance(loaded, dict):
                self.data.update(loaded)

        except Exception as error:
            print("[MEMORY LOAD ERROR]", error)

    def save(self):
        with self.lock:
            try:
                temp = self.file_path + ".tmp"

                with open(
                    temp,
                    "w",
                    encoding="utf-8"
                ) as f:
                    json.dump(
                        self.data,
                        f,
                        ensure_ascii=False,
                        indent=2
                    )

                os.replace(temp, self.file_path)

            except Exception as error:
                print("[MEMORY SAVE ERROR]", error)

    def add_message(self, role, text):
        conversations = self.data.setdefault(
            "conversations",
            []
        )

        conversations.append({
            "role": role,
            "text": text
        })

        if len(conversations) > 1000:
            del conversations[:-1000]

        self.save()

    def _add_long_term_memory(
        self,
        text,
        category="general"
    ):
        if not text:
            return

        text = text.strip()

        if not text or text == "NO_MEMORY":
            return

        memories = self.data.setdefault(
            "memories",
            []
        )

        normalized = text.casefold()

        for memory in memories:
            old = memory.get("text", "").strip().casefold()

            if old == normalized:
                return

        memories.append({
            "text": text,
            "category": category
        })

        self.save()

    def learn_from_text(self, text):
        """
        لا يستخدم كلمات مفتاحية.
        التحليل الفعلي للذاكرة يتم بواسطة brain.py.
        """

        if not text:
            return

        self.data.setdefault("profile", {})
        self.data.setdefault("memories", [])
        self.save()

    def search_memories(self, query, limit=20):
        """
        استرجاع ذاكرة بسيطة حسب الكلمات الموجودة في السؤال.
        """

        if not query:
            return []

        memories = self.data.get(
            "memories",
            []
        )

        query_words = set(
            re.findall(
                r"[\w\u0600-\u06FF]+",
                query.casefold()
            )
        )

        stop_words = {
            "انا", "أنا", "انت", "إنت", "هو", "هي",
            "من", "ما", "ماذا", "ايه", "إيه",
            "عن", "في", "على", "هل", "يا",
            "the", "is", "am", "are", "what",
            "who", "my", "me", "do", "you"
        }

        query_words -= stop_words

        scored = []

        for memory in memories:

            text = memory.get(
                "text",
                ""
            )

            if not text:
                continue

            words = set(
                re.findall(
                    r"[\w\u0600-\u06FF]+",
                    text.casefold()
                )
            )

            score = len(
                query_words & words
            )

            if score > 0:
                scored.append(
                    (score, memory)
                )

        scored.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            memory
            for score, memory in scored[:limit]
        ]

    def get_long_term_context(
        self,
        query="",
        limit=20
    ):
        result = []

        profile = self.data.get(
            "profile",
            {}
        )

        for key, value in profile.items():
            result.append(
                f"{key}: {value}"
            )

        if query:
            memories = self.search_memories(
                query,
                limit
            )
        else:
            memories = self.data.get(
                "memories",
                []
            )[-limit:]

        for memory in memories:

            text = memory.get(
                "text",
                ""
            )

            if text:
                result.append(text)

        return "\n".join(result)

    def get_context(
        self,
        query="",
        limit=20
    ):
        return self.get_long_term_context(
            query,
            limit
        )

    def get_recent(self, limit=20):
        conversations = self.data.get(
            "conversations",
            []
        )

        return conversations[-limit:]

    def clear(self):
        self.data = {
            "profile": {},
            "memories": [],
            "conversations": []
        }

        self.save()

    def count(self):
        return len(
            self.data.get(
                "conversations",
                []
            )
        )
