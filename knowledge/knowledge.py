import os
import re


ROOT_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

KNOWLEDGE_DIR = os.path.join(
    ROOT_DIR,
    "knowledge"
)


class KnowledgeEngine:

    def __init__(self):
        self.documents = []
        self.load()

    def tokenize(self, text):
        return set(
            re.findall(
                r"[a-zA-Z0-9_./:-]+",
                text.lower()
            )
        )

    def load(self):

        self.documents.clear()

        for root, _, files in os.walk(
            KNOWLEDGE_DIR
        ):

            for filename in files:

                if not filename.endswith(
                    (".md", ".txt")
                ):
                    continue

                if filename in [
                    "knowledge.py",
                    "retriever.py"
                ]:
                    continue

                path = os.path.join(
                    root,
                    filename
                )

                try:

                    with open(
                        path,
                        "r",
                        encoding="utf-8"
                    ) as file:

                        text = file.read()

                    if text.strip():

                        self.documents.append(
                            {
                                "path": path,
                                "text": text,
                                "tokens": self.tokenize(
                                    text
                                )
                            }
                        )

                except Exception as error:

                    print(
                        "KNOWLEDGE ERROR:",
                        error
                    )

    def search(
        self,
        query,
        limit=5
    ):

        query_tokens = self.tokenize(
            query
        )

        results = []

        for document in self.documents:

            score = len(
                query_tokens
                &
                document["tokens"]
            )

            if score > 0:

                results.append(
                    {
                        "score": score,
                        "source": document["path"],
                        "text": document["text"]
                    }
                )

        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return results[:limit]

    def context(
        self,
        query,
        limit=5
    ):

        results = self.search(
            query,
            limit
        )

        if not results:
            return ""

        output = []

        for result in results:

            output.append(
                f"SOURCE: {result['source']}\n"
                f"{result['text']}"
            )

        return "\n\n---\n\n".join(
            output
        )


if __name__ == "__main__":

    engine = KnowledgeEngine()

    while True:

        query = input(
            "KNOWLEDGE > "
        ).strip()

        if query.lower() in [
            "exit",
            "quit"
        ]:
            break

        results = engine.search(
            query
        )

        for result in results:

            print(
                "\nSCORE:",
                result["score"]
            )

            print(
                "SOURCE:",
                result["source"]
            )

            print(
                result["text"][:1000]
            )

