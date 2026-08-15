import os
import json
import threading

import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
MIN_SIMILARITY_SCORE = 0.35

_model = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


class JarvisMemory:
    def __init__(self):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.data_dir = os.path.join(base_dir, "data")
        self.file_path = os.path.join(self.data_dir, "memory.json")
        os.makedirs(self.data_dir, exist_ok=True)
        self.lock = threading.Lock()
        self.data = {
            "profile": {},
            "memories": [],
            "conversations": []
        }
        self.load()
        self._backfill_embeddings()

    def load(self):
        if not os.path.exists(self.file_path):
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data.update(loaded)
        except Exception as error:
            print("[MEMORY LOAD ERROR]", error)

    def save(self):
        with self.lock:
            try:
                temp = self.file_path + ".tmp"
                with open(temp, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                os.replace(temp, self.file_path)
            except Exception as error:
                print("[MEMORY SAVE ERROR]", error)

    def add_message(self, role, text):
        conversations = self.data.setdefault("conversations", [])
        conversations.append({"role": role, "text": text})
        if len(conversations) > 1000:
            del conversations[:-1000]
        self.save()

    def _embed(self, text):
        model = get_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def _backfill_embeddings(self):
        memories = self.data.setdefault("memories", [])
        changed = False
        for memory in memories:
            if not memory.get("embedding"):
                text = memory.get("text", "")
                if text:
                    memory["embedding"] = self._embed(text)
                    changed = True
        if changed:
            self.save()

    def _add_long_term_memory(self, text, category="general"):
        if not text:
            return
        text = text.strip()
        if not text or text == "NO_MEMORY":
            return

        memories = self.data.setdefault("memories", [])
        normalized = text.casefold()
        for memory in memories:
            old = memory.get("text", "").strip().casefold()
            if old == normalized:
                return

        memories.append({
            "text": text,
            "category": category,
            "embedding": self._embed(text)
        })
        self.save()

    def learn_from_text(self, text):
        if not text:
            return
        self.data.setdefault("profile", {})
        self.data.setdefault("memories", [])
        self.save()

    def search_memories(self, query, limit=20, min_score=MIN_SIMILARITY_SCORE):
        if not query:
            return []

        memories = self.data.get("memories", [])
        if not memories:
            return []

        query_vector = np.array(self._embed(query))

        scored = []
        for memory in memories:
            embedding = memory.get("embedding")
            if not embedding:
                continue
            vector = np.array(embedding)
            score = float(np.dot(query_vector, vector))
            if score >= min_score:
                scored.append((score, memory))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [memory for score, memory in scored[:limit]]

    def get_long_term_context(self, query="", limit=20):
        result = []
        profile = self.data.get("profile", {})
        for key, value in profile.items():
            result.append(f"{key}: {value}")

        if query:
            memories = self.search_memories(query, limit)
        else:
            memories = self.data.get("memories", [])[-limit:]

        for memory in memories:
            text = memory.get("text", "")
            if text:
                result.append(text)

        return "\n".join(result)

    def get_context(self, query="", limit=20):
        return self.get_long_term_context(query, limit)

    def get_recent(self, limit=20):
        conversations = self.data.get("conversations", [])
        return conversations[-limit:]

    def clear(self):
        self.data = {
            "profile": {},
            "memories": [],
            "conversations": []
        }
        self.save()

    def count(self):
        return len(self.data.get("conversations", []))
