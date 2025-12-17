"""
Institution roster scraping helpers.

Designed to be gentle: if ENT_OFFLINE=true no network calls are made and
callers should use sample data instead.
"""

from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .config import HTTP_TIMEOUT, OFFLINE, USER_AGENT
from .models import Institution


HEADERS = {"User-Agent": USER_AGENT}


def fetch_institution_roster(institution: Institution) -> List[dict]:
    if OFFLINE:
        return []
    url = institution.website
    if not url:
        return []
    if "northwestern" in url:
        return fetch_northwestern(url)

    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    if "uchicago" in url:
        return parse_uchicago(soup, url)
    if "uic.edu" in url:
        return parse_uic(soup, url)
    if "rush.edu" in url:
        return parse_rush(soup, url)

    return generic_people_scrape(soup, url)


def fetch_html(url: str) -> str | None:
    try:
        with httpx.Client(headers=HEADERS, timeout=HTTP_TIMEOUT) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


def fetch_northwestern(base_url: str) -> List[dict]:
    """
    Northwestern faculty pages are paginated (9 pages). Each page has:
    - div.facultyList
      - multiple div.profile.row
        - h3 > a (name + profile link)
        - p.rankDept with title info
    """
    results: List[dict] = []
    seen_pages = set()
    next_url = base_url

    while next_url and next_url not in seen_pages:
        seen_pages.add(next_url)
        html = fetch_html(next_url)
        if not html:
            break
        soup = BeautifulSoup(html, "html.parser")
        results.extend(parse_northwestern_page(soup, base_url))
        next_url = find_next_page(soup, next_url)

    return dedupe(results)


def parse_northwestern_page(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
    cards = soup.select("#facultyList div.profile.row")
    if not cards:
        return generic_people_scrape(soup, base_url)

    for card in cards:
        h3 = card.find("h3")
        link = h3.find("a") if h3 else None

        # Prefer profile links (profile.html?...), avoid mailto/tel anchors.
        if not link or not link.get("href"):
            link = card.find("a", href=re.compile(r"profile", re.I))
        if link and link.get("href", "").startswith(("mailto:", "tel:")):
            link = None

        name = link.get_text(strip=True) if link else (h3.get_text(strip=True) if h3 else None)
        profile_url = urljoin(base_url, link["href"]) if link and link.get("href") else None
        email = None  # NW page does not expose email on the list; leave null.

        if name:
            results.append(
                {
                    "name": name,
                    "email": email,
                    "profile_url": profile_url,
                }
            )
    return results


def find_next_page(soup: BeautifulSoup, current_url: str) -> str | None:
    # Look for pagination links labeled next or with rel/aria markers.
    next_link = soup.find("a", attrs={"aria-label": re.compile("next", re.I)})
    if not next_link:
        next_link = soup.find("a", string=re.compile("next", re.I))
    if not next_link:
        next_link = soup.select_one(".pagination a.next, .pager-next a")
    if next_link and next_link.get("href"):
        return urljoin(current_url, next_link["href"])
    return None


def parse_uchicago(soup: BeautifulSoup, base_url: str) -> List[dict]:
    def _strip_degrees(raw_name: str) -> str:
        # Remove degree suffixes (e.g., ", MD", ", MD, MPH") and stray trailing credentials.
        name = re.sub(r",.*$", "", raw_name).strip()
        name = re.sub(
            r"\s+(MD|DO|MSPA|MSN|MS|MPH|PHD|AUD|PA-C|NP|RN|FACS|CCC-SLP|FAAP|CNM|DNP)\.?$",
            "",
            name,
            flags=re.IGNORECASE,
        )
        return name.strip()

    sections = soup.find_all("section", class_="container")
    start_idx = None
    end_idx = None
    for idx, sec in enumerate(sections):
        heading = sec.find(["h1", "h2", "h3"])
        title = heading.get_text(strip=True) if heading else ""
        if start_idx is None and title == "Our Ear and Hearing Team":
            start_idx = idx
        if title == "Our Voice Center Team":
            end_idx = idx
            break

    if start_idx is None:
        return generic_people_scrape(soup, base_url)
    target_sections = sections[start_idx : end_idx if end_idx is not None else len(sections)]

    results: List[dict] = []
    for sec in target_sections:
        links = sec.select("a.Profile_profile__f6TYC, a[href*='/find-a-physician/physician/']")
        for link in links:
            href = link.get("href")
            if not href or href.startswith(("mailto:", "tel:")):
                continue
            name_el = link.find(["h3", "h4"])
            name = name_el.get_text(" ", strip=True) if name_el else link.get_text(" ", strip=True)
            if not name:
                img = link.find("img")
                alt = img.get("alt") if img else None
                name = alt.strip() if alt else ""
            name = _strip_degrees(name)
            if not name:
                continue
            profile_url = urljoin(base_url, href)
            results.append({"name": name, "email": None, "profile_url": profile_url})

    return dedupe(results) if results else generic_people_scrape(soup, base_url)


def parse_uic(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
    # New UIC layout: directory-list > profile-teaser cards
    teaser_cards = soup.select(".directory-list.list--flat .profile-teaser")
    if teaser_cards:
        for card in teaser_cards:
            name_el = card.select_one("._name a, ._name")
            name = name_el.get_text(" ", strip=True) if name_el else card.get_text(" ", strip=True)

            email_el = card.find("a", href=re.compile(r"mailto:", re.I))
            email = email_el.get("href", "").split("mailto:")[-1] if email_el else None

            link = card.select_one("._name a") or card.find(
                "a", href=re.compile(r"profiles/", re.I)
            )
            if not link:
                link = card.find("a", href=True)
            profile_url = None
            if link:
                href = link.get("href")
                if href and not href.startswith(("mailto:", "tel:")):
                    profile_url = urljoin(base_url, href)

            if name:
                results.append({"name": name, "email": email, "profile_url": profile_url})

        return dedupe(results)

    # Fallback to older structures
    cards = soup.select(".faculty-list .person, .profile-card")
    for card in cards:
        name_el = card.select_one(".person-name, h3, h4")
        name = name_el.get_text(strip=True) if name_el else card.get_text(" ", strip=True)
        email_el = card.find("a", href=re.compile(r"mailto:"))
        email = email_el.get("href", "").split("mailto:")[-1] if email_el else None
        profile_link = card.find("a", href=True)
        profile_url = None
        if profile_link:
            href = profile_link.get("href")
            if href and not href.startswith("mailto:"):
                profile_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
        if name:
            results.append({"name": name, "email": email, "profile_url": profile_url})
    return dedupe(results)


def parse_rush(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
    cards = soup.select(".views-row, .provider-card")
    for card in cards:
        name_el = card.select_one("h3, h2, .provider-name")
        name = name_el.get_text(strip=True) if name_el else card.get_text(" ", strip=True)
        email = None
        profile_url = None
        link = card.find("a", href=True)
        if link:
            href = link.get("href")
            if href and not href.startswith("mailto:"):
                profile_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
        if name:
            results.append({"name": name, "email": email, "profile_url": profile_url})
    return dedupe(results)


def generic_people_scrape(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if not text:
            continue
        if "mailto:" in href:
            email = href.split("mailto:")[-1]
            results.append({"name": text, "email": email, "profile_url": None})
        elif re.search(r"/(faculty|people|profile)", href):
            results.append(
                {
                    "name": text,
                    "email": None,
                    "profile_url": href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/"),
                }
            )
    return dedupe(results)


def dedupe(records: List[dict]) -> List[dict]:
    seen = set()
    unique = []
    for r in records:
        key = (r.get("name"), r.get("email"), r.get("profile_url"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique
