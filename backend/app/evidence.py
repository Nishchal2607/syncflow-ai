"""Controlled evidence retrieval for deterministic and live-safe operation."""
from datetime import datetime, timezone
import re


LOCAL_DOCUMENTS = [
    {
        "document_id": "local-ev-001",
        "title": "Electric vehicle market demo fixture",
        "url": "local://fixtures/electric-vehicles",
        "excerpt": "Tesla and Rivian are electric vehicle companies; battery range and pricing vary by model.",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
        "keywords": ("electric", "vehicle", "tesla", "rivian", "battery"),
    },
    {
        "document_id": "local-db-001",
        "title": "Cloud database demo fixture",
        "url": "local://fixtures/cloud-databases",
        "excerpt": "PostgreSQL-compatible managed databases include Amazon RDS and Google Cloud SQL.",
        "retrieved_at": "2026-01-01T00:00:00+00:00",
        "keywords": ("cloud", "database", "postgresql", "amazon", "google"),
    },
]


def sanitize_external_text(text: str) -> str:
    return re.sub(r"(?is)(ignore|disregard|override).{0,100}(instruction|system|developer)", "[filtered instruction]", text)


def retrieve(query: str) -> list[dict]:
    words = {word.lower().strip(".,!?;:")
             for word in sanitize_external_text(query).split()
             if len(word.strip(".,!?;:")) >= 4}
    matches = []
    for document in LOCAL_DOCUMENTS:
        score = len(words.intersection(document["keywords"]))
        if score:
            matches.append({
                "title": document["title"],
                "url": document["url"],
                "document_id": document["document_id"],
                "excerpt": sanitize_external_text(document["excerpt"]),
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
                "fixture_retrieval": True,
                "match_score": score,
                "status": "supported",
            })
    return matches


def verify_claim(claim: str, evidence: list[dict]) -> str:
    if not evidence:
        return "insufficient_evidence"
    lowered = claim.lower()
    if any("contradict" in item.get("excerpt", "").lower() for item in evidence):
        return "contradicted"
    if any(word in item.get("excerpt", "").lower() for item in evidence for word in lowered.split() if len(word) >= 5):
        return "supported"
    return "unverified"
