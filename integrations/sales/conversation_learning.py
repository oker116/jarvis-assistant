import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ConversationLearning:
    """
    Conversation tracking + outcome learning layer.

    Uses the existing sales.db schema:
        leads
        events
        outcomes
        learning_stats
    """

    def __init__(self, db_path=None):
        root = Path(__file__).resolve().parents[2]

        self.db_path = Path(
            db_path or root / "data" / "sales.db"
        )

    def _connect(self):
        return sqlite3.connect(str(self.db_path))

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def ensure_lead(self, lead_id, name=None, source="whatsapp",
                    metadata=None):

        now = self._now()

        with self._connect() as con:
            cur = con.cursor()

            row = cur.execute(
                """
                SELECT lead_id
                FROM leads
                WHERE lead_id = ?
                """,
                (lead_id,)
            ).fetchone()

            if row:
                cur.execute(
                    """
                    UPDATE leads
                    SET updated_at = ?
                    WHERE lead_id = ?
                    """,
                    (now, lead_id)
                )
                return False

            cur.execute(
                """
                INSERT INTO leads (
                    lead_id,
                    created_at,
                    updated_at,
                    name,
                    source,
                    status,
                    score,
                    priority,
                    paid,
                    revenue,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    now,
                    now,
                    name or lead_id,
                    source,
                    "new",
                    0,
                    "UNKNOWN",
                    0,
                    0,
                    json.dumps(
                        metadata or {},
                        ensure_ascii=False
                    )
                )
            )

            return True

    def record_message(
        self,
        lead_id,
        content,
        actor="customer",
        channel="whatsapp",
        metadata=None
    ):

        self.ensure_lead(
            lead_id=lead_id,
            source=channel
        )

        with self._connect() as con:
            con.execute(
                """
                INSERT INTO events (
                    lead_id,
                    timestamp,
                    event_type,
                    channel,
                    actor,
                    content,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    self._now(),
                    "message_received"
                    if actor == "customer"
                    else "message_sent",
                    channel,
                    actor,
                    content,
                    json.dumps(
                        metadata or {},
                        ensure_ascii=False
                    )
                )
            )

    def set_stage(self, lead_id, stage, score=None,
                  priority=None):

        allowed = {
            "new",
            "contacted",
            "interested",
            "qualified",
            "negotiating",
            "won",
            "lost"
        }

        if stage not in allowed:
            raise ValueError(
                f"Invalid stage: {stage}"
            )

        with self._connect() as con:
            if score is None and priority is None:
                con.execute(
                    """
                    UPDATE leads
                    SET status = ?,
                        updated_at = ?
                    WHERE lead_id = ?
                    """,
                    (
                        stage,
                        self._now(),
                        lead_id
                    )
                )

            else:
                con.execute(
                    """
                    UPDATE leads
                    SET status = ?,
                        score = COALESCE(?, score),
                        priority = COALESCE(?, priority),
                        updated_at = ?
                    WHERE lead_id = ?
                    """,
                    (
                        stage,
                        score,
                        priority,
                        self._now(),
                        lead_id
                    )
                )

    def record_outcome(
        self,
        lead_id,
        outcome,
        revenue=0,
        reason=None,
        metadata=None
    ):

        valid = {
            "won",
            "lost",
            "interested",
            "not_interested",
            "no_response"
        }

        if outcome not in valid:
            raise ValueError(
                f"Invalid outcome: {outcome}"
            )

        now = self._now()

        with self._connect() as con:

            # --------------------------------------------------
            # Find the latest outreach style used for this lead.
            # --------------------------------------------------

            style_row = con.execute(
                """
                SELECT metadata_json
                FROM events
                WHERE lead_id = ?
                  AND event_type = 'offer_prepared'
                ORDER BY id DESC
                LIMIT 1
                """,
                (lead_id,)
            ).fetchone()

            used_style = None

            if style_row:
                try:
                    style_metadata = json.loads(
                        style_row[0] or "{}"
                    )
                    used_style = style_metadata.get("style")
                except Exception:
                    used_style = None

            # --------------------------------------------------
            # Record outcome.
            # --------------------------------------------------

            con.execute(
                """
                INSERT INTO outcomes (
                    lead_id,
                    timestamp,
                    outcome,
                    revenue,
                    reason,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    now,
                    outcome,
                    float(revenue or 0),
                    reason,
                    json.dumps(
                        metadata or {},
                        ensure_ascii=False
                    )
                )
            )

            # --------------------------------------------------
            # Update lead status.
            # --------------------------------------------------

            if outcome == "won":
                status = "won"
                paid = 1

            elif outcome == "lost":
                status = "lost"
                paid = 0

            elif outcome == "interested":
                status = "interested"
                paid = 0

            elif outcome == "not_interested":
                status = "lost"
                paid = 0

            else:
                status = "contacted"
                paid = 0

            con.execute(
                """
                UPDATE leads
                SET status = ?,
                    paid = ?,
                    revenue = ?,
                    updated_at = ?
                WHERE lead_id = ?
                """,
                (
                    status,
                    paid,
                    float(revenue or 0),
                    now,
                    lead_id
                )
            )

            # --------------------------------------------------
            # Global outcome learning.
            # --------------------------------------------------

            key = f"outcome:{outcome}"

            row = con.execute(
                """
                SELECT observations,
                       successes,
                       failures,
                       total_revenue
                FROM learning_stats
                WHERE key = ?
                """,
                (key,)
            ).fetchone()

            observations = (row[0] if row else 0) + 1
            successes = (row[1] if row else 0)
            failures = (row[2] if row else 0)
            total_revenue = (
                row[3] if row else 0
            ) + float(revenue or 0)

            if outcome in {"won", "interested"}:
                successes += 1

            elif outcome in {
                "lost",
                "not_interested"
            }:
                failures += 1

            con.execute(
                """
                INSERT INTO learning_stats (
                    key,
                    observations,
                    successes,
                    failures,
                    total_revenue,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    observations = excluded.observations,
                    successes = excluded.successes,
                    failures = excluded.failures,
                    total_revenue = excluded.total_revenue,
                    updated_at = excluded.updated_at
                """,
                (
                    key,
                    observations,
                    successes,
                    failures,
                    total_revenue,
                    now
                )
            )

            # --------------------------------------------------
            # Style -> Outcome learning.
            # --------------------------------------------------

            if used_style:

                style_key = f"style:{used_style}"

                row = con.execute(
                    """
                    SELECT observations,
                           successes,
                           failures,
                           total_revenue
                    FROM learning_stats
                    WHERE key = ?
                    """,
                    (style_key,)
                ).fetchone()

                style_observations = (
                    row[0] if row else 0
                ) + 1

                style_successes = (
                    row[1] if row else 0
                )

                style_failures = (
                    row[2] if row else 0
                )

                style_revenue = (
                    row[3] if row else 0
                ) + float(revenue or 0)

                if outcome in {"won", "interested"}:
                    style_successes += 1

                elif outcome in {
                    "lost",
                    "not_interested"
                }:
                    style_failures += 1

                con.execute(
                    """
                    INSERT INTO learning_stats (
                        key,
                        observations,
                        successes,
                        failures,
                        total_revenue,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        observations = excluded.observations,
                        successes = excluded.successes,
                        failures = excluded.failures,
                        total_revenue = excluded.total_revenue,
                        updated_at = excluded.updated_at
                    """,
                    (
                        style_key,
                        style_observations,
                        style_successes,
                        style_failures,
                        style_revenue,
                        now
                    )
                )

                # More explicit per-outcome style statistic.
                pair_key = (
                    f"style_outcome:"
                    f"{used_style}:{outcome}"
                )

                pair_row = con.execute(
                    """
                    SELECT observations,
                           successes,
                           failures,
                           total_revenue
                    FROM learning_stats
                    WHERE key = ?
                    """,
                    (pair_key,)
                ).fetchone()

                pair_observations = (
                    pair_row[0] if pair_row else 0
                ) + 1

                pair_successes = (
                    pair_row[1] if pair_row else 0
                )

                pair_failures = (
                    pair_row[2] if pair_row else 0
                )

                pair_revenue = (
                    pair_row[3] if pair_row else 0
                ) + float(revenue or 0)

                if outcome in {"won", "interested"}:
                    pair_successes += 1

                elif outcome in {
                    "lost",
                    "not_interested"
                }:
                    pair_failures += 1

                con.execute(
                    """
                    INSERT INTO learning_stats (
                        key,
                        observations,
                        successes,
                        failures,
                        total_revenue,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        observations = excluded.observations,
                        successes = excluded.successes,
                        failures = excluded.failures,
                        total_revenue = excluded.total_revenue,
                        updated_at = excluded.updated_at
                    """,
                    (
                        pair_key,
                        pair_observations,
                        pair_successes,
                        pair_failures,
                        pair_revenue,
                        now
                    )
                )

    def get_conversation(self, lead_id, limit=50):

        with self._connect() as con:
            rows = con.execute(
                """
                SELECT timestamp,
                       channel,
                       actor,
                       event_type,
                       content,
                       metadata_json
                FROM events
                WHERE lead_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (lead_id, limit)
            ).fetchall()

        return [
            {
                "timestamp": row[0],
                "channel": row[1],
                "actor": row[2],
                "event_type": row[3],
                "content": row[4],
                "metadata": json.loads(row[5] or "{}")
            }
            for row in rows
        ]


    def record_offer_style(
        self,
        lead_id,
        style,
        service=None,
        score=None
    ):
        """
        Record which outreach style was used.

        This is an observation only.
        It does not send anything.
        """

        metadata = {
            "style": style,
            "service": service,
            "score": score,
        }

        self.ensure_lead(
            lead_id=lead_id,
            source="outreach"
        )

        with self._connect() as con:
            con.execute(
                """
                INSERT INTO events (
                    lead_id,
                    timestamp,
                    event_type,
                    channel,
                    actor,
                    content,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    self._now(),
                    "offer_prepared",
                    "sales",
                    "jarvis",
                    None,
                    json.dumps(
                        metadata,
                        ensure_ascii=False
                    )
                )
            )

            key = f"style:{style}"

            row = con.execute(
                """
                SELECT observations,
                       successes,
                       failures,
                       total_revenue
                FROM learning_stats
                WHERE key = ?
                """,
                (key,)
            ).fetchone()

            observations = (row[0] if row else 0) + 1
            successes = row[1] if row else 0
            failures = row[2] if row else 0
            revenue = row[3] if row else 0

            con.execute(
                """
                INSERT INTO learning_stats (
                    key,
                    observations,
                    successes,
                    failures,
                    total_revenue,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    observations = excluded.observations,
                    updated_at = excluded.updated_at
                """,
                (
                    key,
                    observations,
                    successes,
                    failures,
                    revenue,
                    self._now()
                )
            )

    def best_offer_style(self, minimum_observations=3):
        """
        Select the best observed outreach style.

        Requires enough observations before exploitation.
        """

        with self._connect() as con:
            rows = con.execute(
                """
                SELECT key,
                       observations,
                       successes,
                       failures,
                       total_revenue
                FROM learning_stats
                WHERE key LIKE 'style:%'
                """
            ).fetchall()

        candidates = []

        for row in rows:
            key = row[0]
            observations = int(row[1] or 0)
            successes = int(row[2] or 0)
            revenue = float(row[4] or 0)

            if observations < minimum_observations:
                continue

            win_rate = successes / observations

            candidates.append({
                "style": key.replace(
                    "style:", ""
                ),
                "observations": observations,
                "successes": successes,
                "win_rate": win_rate,
                "revenue": revenue,
            })

        if not candidates:
            return None

        candidates.sort(
            key=lambda x: (
                x["win_rate"],
                x["revenue"]
            ),
            reverse=True
        )

        return candidates[0]

    def learning_summary(self):

        with self._connect() as con:
            rows = con.execute(
                """
                SELECT key,
                       observations,
                       successes,
                       failures,
                       total_revenue
                FROM learning_stats
                ORDER BY total_revenue DESC
                """
            ).fetchall()

        return [
            {
                "key": row[0],
                "observations": row[1],
                "successes": row[2],
                "failures": row[3],
                "revenue": row[4]
            }
            for row in rows
        ]


if __name__ == "__main__":

    engine = ConversationLearning()

    print("Conversation Learning initialized.")
    print("Database:", engine.db_path)

    print("\nLearning summary:")
    print(
        json.dumps(
            engine.learning_summary(),
            indent=2,
            ensure_ascii=False
        )
    )
