"""Parse Where's My MEP profile pages (SSR HTML — no browser needed)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape

from transparent_scrape.core.http import get_text

WMM_BASE = "https://www.wheresmymep.eu/mep"


@dataclass
class WmmActivity:
    role: str
    income_label: str
    activity_type: str

    @property
    def income_eur(self) -> int | None:
        if "unpaid" in self.income_label.lower():
            return 0
        m = re.search(r"€([\d,]+)", self.income_label)
        if not m:
            return None
        return int(m.group(1).replace(",", ""))

    @property
    def flow(self) -> str:
        if self.income_eur and self.income_eur > 0:
            if self.activity_type.lower() == "employment":
                if "counsel" in self.role.lower() or "lawyer" in self.role.lower():
                    return "advisory_paid"
                return "receives"
            return "receives"
        return "member_unpaid"

    @property
    def organization(self) -> str:
        if " - " in self.role:
            return self.role.split(" - ")[-1].strip()
        return self.role.strip()[:80]


@dataclass
class WmmMeeting:
    date: str
    organization: str
    subject: str

    @property
    def iso_date(self) -> str:
        from datetime import datetime

        try:
            return datetime.strptime(self.date.strip(), "%d %b %Y").strftime("%Y-%m-%d")
        except ValueError:
            return self.date.strip()


@dataclass
class WmmProfile:
    mep_id: str
    income_min: int | None = None
    income_max: int | None = None
    activities: list[WmmActivity] = field(default_factory=list)
    meetings: list[WmmMeeting] = field(default_factory=list)
    name: str | None = None
    political_group: str | None = None
    country: str | None = None

    @property
    def has_no_meetings(self) -> bool:
        return "no lobby meetings recorded" in self._raw_lower

    _raw_lower: str = ""


def fetch_wmm_html(mep_id: str) -> str:
    return get_text(f"{WMM_BASE}/{mep_id}")


def _parse_income_band(html: str) -> tuple[int | None, int | None]:
    if "no current outside activities" in html.lower():
        return 0, 0
    m = re.search(r"declared outside income of €([\d,]+)[–-]€?([\d,]+)/year", html, re.I)
    if not m:
        m = re.search(r"€([\d,]+)[–-]€([\d,]+)/year", html)
    if not m:
        if re.search(r"€0[–-]€?0/year|€0–0/year", html):
            return 0, 0
        return None, None
    return int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))


def _parse_meta(html: str) -> tuple[str | None, str | None, str | None]:
    title_m = re.search(r"<title>([^<]+)</title>", html)
    name = None
    if title_m:
        name = title_m.group(1).split(" MEP")[0].strip()
    desc_m = re.search(r'<meta name="description" content="([^"]+)"', html)
    group = country = None
    if desc_m:
        desc = unescape(desc_m.group(1))
        parts = [p.strip() for p in desc.split("·")]
        if len(parts) >= 2:
            country = parts[-2].split(".")[0].strip() if len(parts) >= 3 else parts[0].split(".")[-1].strip()
            group = parts[-1].split(".")[0].strip()
        if "Germany" in desc:
            country = "DE"
    return name, country, group


def _parse_activities(html: str) -> list[WmmActivity]:
    rows = re.findall(
        r'col-span-6 text-sm font-medium[^>]*>([^<]+)</span>'
        r'<span class="col-span-3 text-sm[^>]*>([^<]+)</span>'
        r"[\s\S]*?"
        r">(Employment|Board|Other|Gift|Gift/Hospitality)<",
        html,
    )
    out: list[WmmActivity] = []
    for role, income, atype in rows:
        role = unescape(re.sub(r"\s+", " ", role)).strip()
        income = unescape(income).strip()
        if role.lower().startswith("activity") or role.lower().startswith("income"):
            continue
        out.append(WmmActivity(role=role, income_label=income, activity_type=atype))
    return out


def _parse_meetings(html: str) -> list[WmmMeeting]:
    if "no lobby meetings recorded" in html.lower():
        return []
    start = html.find("Recent Lobby Meetings")
    if start < 0:
        return []
    section = html[start : start + 50000]
    pattern = re.compile(
        r'col-span-2 text-xs[^>]*>(\d{1,2} \w+ \d{4})</span>'
        r'<span class="col-span-4 text-sm font-medium[^>]*>'
        r"(?:<a[^>]*>)?([^<]+?)(?:</a>)?"
        r'</span><span class="col-span-6 text-sm[^>]*>(.*?)</span></div>',
        re.S,
    )
    out: list[WmmMeeting] = []
    for date, org, subject in pattern.findall(section):
        org = unescape(re.sub(r"\s+", " ", org)).strip()
        subject = unescape(re.sub(r"<[^>]+>", " ", subject))
        subject = re.sub(r"\s+", " ", subject).strip()
        out.append(WmmMeeting(date=date.strip(), organization=org, subject=subject))
    return out


def parse_wmm_profile(mep_id: str, html: str) -> WmmProfile:
    income_min, income_max = _parse_income_band(html)
    name, country, group = _parse_meta(html)
    profile = WmmProfile(
        mep_id=mep_id,
        income_min=income_min,
        income_max=income_max,
        activities=_parse_activities(html),
        meetings=_parse_meetings(html),
        name=name,
        country=country,
        political_group=group,
    )
    profile._raw_lower = html.lower()
    return profile


def load_wmm_profile(mep_id: str) -> WmmProfile:
    html = fetch_wmm_html(mep_id)
    return parse_wmm_profile(mep_id, html)


def _activity_to_dict(a: WmmActivity) -> dict:
    return {
        "role": a.role,
        "income_label": a.income_label,
        "income_eur": a.income_eur,
        "activity_type": a.activity_type,
        "flow": a.flow,
        "organization": a.organization,
        "is_gift": a.activity_type.lower() in ("gift", "gift/hospitality"),
    }


def _meeting_to_dict(m: WmmMeeting) -> dict:
    return {
        "date": m.date,
        "iso_date": m.iso_date,
        "organization": m.organization,
        "subject": m.subject,
    }


def profile_to_dict(profile: WmmProfile) -> dict:
    from datetime import datetime, timezone

    gifts = [a for a in profile.activities if a.activity_type.lower() in ("gift", "gift/hospitality")]
    paid = [a for a in profile.activities if a.income_eur and a.income_eur > 0]
    return {
        "source": "wmm",
        "mep_id": profile.mep_id,
        "name": profile.name,
        "country": profile.country,
        "political_group": profile.political_group,
        "income_min_eur": profile.income_min,
        "income_max_eur": profile.income_max,
        "has_no_meetings": profile.has_no_meetings,
        "activities": [_activity_to_dict(a) for a in profile.activities],
        "meetings": [_meeting_to_dict(m) for m in profile.meetings],
        "gifts_hospitality": [_activity_to_dict(a) for a in gifts],
        "paid_activities_count": len(paid),
        "meetings_count": len(profile.meetings),
        "source_url": f"{WMM_BASE}/{profile.mep_id}",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_and_save(mep_id: str, out_dir: Path, *, skip_existing: bool = False) -> Path:
    from transparent_scrape.core.storage import save_json

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{mep_id}.json"
    if skip_existing and out.exists():
        return out
    profile = load_wmm_profile(mep_id)
    save_json(out, profile_to_dict(profile))
    return out


def batch_fetch(
    parsed_dir: Path,
    *,
    term: int = 10,
    limit: int | None = None,
    country: str | None = None,
    skip_existing: bool = True,
    delay: float = 1.0,
) -> dict:
    import time

    from transparent_scrape.core.storage import load_json, save_json, update_manifest
    from transparent_scrape.sources import ep_api

    wmm_dir = parsed_dir / "wmm"
    wmm_dir.mkdir(parents=True, exist_ok=True)
    roster_path = parsed_dir / "meps" / f"term_{term}.json"
    if not roster_path.exists():
        ep_api.fetch_and_save_roster(parsed_dir, term)

    roster = load_json(roster_path).get("meps") or []
    errors: list[dict] = []
    done = 0
    skipped = 0

    for row in roster:
        if limit and done >= limit:
            break
        pid = row["identifier"]
        out = wmm_dir / f"{pid}.json"
        if skip_existing and out.exists():
            skipped += 1
            continue
        if country:
            meta_path = parsed_dir / "meps" / f"{pid}.json"
            if meta_path.exists():
                meta = load_json(meta_path)
            else:
                meta = ep_api.enrich_mep(pid, term)
            c = (meta.get("country") or row.get("country") or "").lower()
            want = country.lower()
            if want == "de" and c not in ("germany", "de", "deu"):
                continue
            elif want != "de" and want not in c:
                continue
        try:
            fetch_and_save(pid, wmm_dir, skip_existing=False)
            done += 1
            print(f"wmm {done}: ok {pid}")
            if done % 10 == 0:
                print(f"wmm batch: {done} fetched")
        except Exception as exc:
            errors.append({"mep_id": pid, "error": str(exc)})
        time.sleep(delay)

    if errors:
        save_json(wmm_dir / "_errors.json", {"errors": errors})
    update_manifest(parsed_dir, "wmm", {"fetched": done, "skipped": skipped, "errors": len(errors)})
    return {"done": done, "skipped": skipped, "errors": errors}
