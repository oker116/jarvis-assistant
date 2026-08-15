from collections import defaultdict

from integrations.sales.sales_memory import SalesMemory


class SalesLearningEngine:
    """
    Learns from ALL recorded outcomes.

    It does not rewrite source code or mutate the core Brain.
    It updates persistent statistics that can improve:
    - lead scoring
    - offer selection
    - message selection
    - follow-up decisions
    """

    SUCCESS_OUTCOMES = {
        "paid",
        "won",
        "closed"
    }

    def __init__(self, memory=None):
        self.memory = memory or SalesMemory()

    def rebuild(self):
        outcomes = self.memory.get_outcomes()

        stats = defaultdict(
            lambda: {
                "observations": 0,
                "successes": 0,
                "failures": 0,
                "revenue": 0.0
            }
        )

        for outcome in outcomes:
            metadata = outcome.get("metadata_json") or {}

            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata)
                except Exception:
                    metadata = {}

            features = metadata.get(
                "features",
                {}
            )

            outcome_name = str(
                outcome.get("outcome", "")
            ).lower()

            success = outcome_name in self.SUCCESS_OUTCOMES

            for feature_name, feature_value in features.items():
                key = self._feature_key(
                    feature_name,
                    feature_value
                )

                stats[key]["observations"] += 1

                if success:
                    stats[key]["successes"] += 1
                else:
                    stats[key]["failures"] += 1

                stats[key]["revenue"] += float(
                    outcome.get("revenue") or 0
                )

        for key, value in stats.items():
            self._save_stat(
                key,
                value
            )

        return self.summary()

    def _save_stat(self, key, value):
        with self.memory._connect() as db:
            db.execute("""
                INSERT INTO learning_stats (
                    key,
                    observations,
                    successes,
                    failures,
                    total_revenue,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key)
                DO UPDATE SET
                    observations=excluded.observations,
                    successes=excluded.successes,
                    failures=excluded.failures,
                    total_revenue=excluded.total_revenue,
                    updated_at=excluded.updated_at
            """, (
                key,
                value["observations"],
                value["successes"],
                value["failures"],
                value["revenue"],
                self.memory.now()
            ))

    @staticmethod
    def _feature_key(name, value):
        return f"{name}={value}"

    def probability(self, feature_name, feature_value):
        key = self._feature_key(
            feature_name,
            feature_value
        )

        with self.memory._connect() as db:
            row = db.execute("""
                SELECT observations, successes
                FROM learning_stats
                WHERE key=?
            """, (key,)).fetchone()

        if not row:
            return None

        observations = int(
            row["observations"] or 0
        )

        successes = int(
            row["successes"] or 0
        )

        # Laplace smoothing
        return (
            successes + 1
        ) / (
            observations + 2
        )

    def summary(self):
        with self.memory._connect() as db:
            rows = db.execute("""
                SELECT
                    key,
                    observations,
                    successes,
                    failures,
                    total_revenue
                FROM learning_stats
                ORDER BY total_revenue DESC
            """).fetchall()

        results = []

        for row in rows:
            observations = int(
                row["observations"] or 0
            )

            successes = int(
                row["successes"] or 0
            )

            rate = (
                successes / observations
                if observations
                else 0
            )

            results.append({
                "feature": row["key"],
                "observations": observations,
                "successes": successes,
                "failures": int(
                    row["failures"] or 0
                ),
                "conversion_rate": round(
                    rate,
                    4
                ),
                "revenue": float(
                    row["total_revenue"] or 0
                )
            })

        return results
