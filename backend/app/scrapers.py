"""
Institution roster scraping helpers.

Designed to be gentle: if ENT_OFFLINE=true no network calls are made and
callers should use sample data instead.
"""

from __future__ import annotations

import re
from typing import List

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
    html = fetch_html(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")

    if "northwestern" in url:
        return parse_northwestern(soup, url)
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


def parse_northwestern(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
    cards = soup.select(".faculty-listing .faculty-list-item, .faculty-list .person")
    if not cards:
        return generic_people_scrape(soup, base_url)
    for card in cards:
        name = card.get_text(" ", strip=True)
        link = card.find("a")
        email = None
        profile_url = None
        if link and link.get("href"):
            href = link.get("href")
            if href.startswith("mailto:"):
                email = href.split("mailto:")[-1]
            else:
                profile_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
                name = link.get_text(" ", strip=True) or name
        if name:
            results.append({"name": name, "email": email, "profile_url": profile_url})
    return dedupe(results)


def parse_uchicago(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
    cards = soup.select(".card-provider, .physician-listing")
    for card in cards:
        name_el = card.select_one("h3, .card-title")
        name = name_el.get_text(strip=True) if name_el else card.get_text(" ", strip=True)
        email = None
        profile_url = None
        profile_link = card.find("a")
        if profile_link and profile_link.get("href"):
            href = profile_link.get("href")
            profile_url = href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
        if name:
            results.append({"name": name, "email": email, "profile_url": profile_url})
    return dedupe(results)


def parse_uic(soup: BeautifulSoup, base_url: str) -> List[dict]:
    results = []
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
