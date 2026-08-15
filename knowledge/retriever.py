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


class KnowledgeRetriever:

    def __init__(self, knowledge_dir=KNOWLEDGE_DIR):
        self.knowledge_dir = knowledge_dir

    def _tokenize(self, text):
        return set(
            re.findall(
                r"[a-zA-Z0-9_./:-]+",
                text.lower()
            )
        )

    def _load_documents(self):
        documents = []

        for root, _, files in os.walk(
            self.knowledge_dir
        ):

            for filename in files:

                if not filename.endswith(
                    (".txt", ".md")
                ):
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

                        documents.append(
                            {
                                "path": path,
                                "text": text
                            }
                        )

                except Exception as error:

                    print(
                        "KNOWLEDGE LOAD ERROR:",
                        path,
                        error
                    )

        return documents

    def search(
        self,
        query,
        limit=5
    ):

        query_tokens = self._tokenize(
            query
        )

        if not query_tokens:
            return []

        results = []

        for document in self._load_documents():

            document_tokens = self._tokenize(
                document["text"]
            )

            score = len(
                query_tokens
                &
                document_tokens
            )

            if score <= 0:
                continue

            results.append(
                {
                    "score": score,
                    "path": document["path"],
                    "text": document["text"]
                }
            )

        results.sort(
            key=lambda item: item["score"],
            reverse=True
        )

        return results[:limit]


if __name__ == "__main__":

    retriever = KnowledgeRetriever()

    print("=" * 60)
    print("JARVIS KNOWLEDGE RETRIEVER")
    print("=" * 60)

    while True:

        query = input(
            "\nSEARCH > "
        ).strip()

        if query.lower() in [
            "exit",
            "quit"
        ]:
            break

        results = retriever.search(
            query
        )

        if not results:

            print(
                "No knowledge found."
            )

            continue

        for result in results:

            print("\n" + "-" * 60)

            print(
                "SCORE:",
                result["score"]
            )

            print(
                "SOURCE:",
                result["path"]
            )

            print(
                result["text"][:1500]
            )

            print("-" * 60)
