"""Build the UnderCover database from the business data in data/."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from backend.db import SCHEMA, db_path

DATA = Path(__file__).parent.parent / "data"


def load(name: str) -> Any:
    """Load one JSON file from data/."""
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def seed(path: Path) -> dict[str, int]:
    """Create a fresh database at path and return how many records it loaded."""
    path.unlink(missing_ok=True)
    claims = load("claims.json")
    policies = load("policies.json")
    customers = load("customers.json")
    handlers = load("handlers.json")
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO claims VALUES (?, ?, ?, 'waiting', NULL, ?)",
            [
                (c["claim_id"], c["policy_id"], c["customer_id"], json.dumps(c))
                for c in claims
            ],
        )
        connection.executemany(
            "INSERT INTO policies VALUES (?, ?)",
            [(p["policy_id"], json.dumps(p)) for p in policies],
        )
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?)",
            [(c["customer_id"], json.dumps(c)) for c in customers],
        )
        connection.executemany(
            "INSERT INTO handlers VALUES (?, ?)",
            [(h["handler_id"], json.dumps(h)) for h in handlers],
        )
    return {
        "claims": len(claims),
        "policies": len(policies),
        "customers": len(customers),
        "handlers": len(handlers),
    }


def main() -> None:
    """Rebuild the database and print what it holds."""
    counts = seed(db_path())
    print("Seeded " + ", ".join(f"{n} {name}" for name, n in counts.items()))


if __name__ == "__main__":
    main()
