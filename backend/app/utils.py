from __future__ import annotations

import datetime as dt
from typing import Iterable


def parse_pub_date(value: str | None) -> dt.date | None:
    """Best-effort parser for publication dates."""

    if not value:
        return None
    value = value.strip()
    formats = ("%Y-%m-%d", "%Y-%m", "%Y")
    for fmt in formats:
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    # Fallback: try splitting on "T" and parse date portion.
    if "T" in value:
        return parse_pub_date(value.split("T", 1)[0])
    return None


def has_recent_publication(publications: Iterable[object], months: int = 3) -> bool:
    """Return True if any publication is within the last `months` months."""

    cutoff = dt.date.today() - dt.timedelta(days=months * 30)
    for pub in publications or []:
        published_on = getattr(pub, "published_on", None) or (
            pub.get("published_on") if isinstance(pub, dict) else None
        )
        pub_date = parse_pub_date(published_on)
        if pub_date and pub_date >= cutoff:
            return True
    return False
