from asyncio import sleep
from datetime import datetime, timedelta

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from app.adapters.base import JobFilters, RawJob, title_allowed

logger = structlog.get_logger()


BG_MONTHS = {
    "яну": 1,
    "фев": 2,
    "мар": 3,
    "апр": 4,
    "май": 5,
    "юни": 6,
    "юли": 7,
    "авг": 8,
    "сеп": 9,
    "окт": 10,
    "ное": 11,
    "дек": 12,
}


class DevBgAdapter:
    async def fetch_jobs(self, filters: JobFilters) -> list[RawJob]:
        result = []
        page = 1
        async with httpx.AsyncClient(follow_redirects=True) as client:
            while True:
                try:
                    if page == 1:
                        url = "https://dev.bg/company/jobs/junior-intern"
                    else:
                        url = f"https://dev.bg/company/jobs/junior-intern/page/{page}"

                    response = await client.get(url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "html.parser")
                    cards = soup.select("div.job-list-item")

                    if not cards:
                        break

                    filtered: list[Tag] = list(cards)

                    if filters.keywords:
                        keywords = [kw.lower() for kw in filters.keywords]
                        prev = filtered
                        filtered = []
                        for card in prev:
                            title_el = card.select_one("h6.job-title")
                            if not title_el:
                                continue
                            title = title_el.get_text(strip=True).lower()
                            if any(keyword in title for keyword in keywords):
                                filtered.append(card)

                    if filters.posted_within_days > 0:
                        prev = filtered
                        filtered = []

                        cutoff = datetime.now() - timedelta(days=filters.posted_within_days)
                        for card in prev:
                            date_el = card.select_one("span.date")
                            if not date_el:
                                continue
                            date_str = date_el.get_text(strip=True)

                            try:
                                day_str, month_str = date_str.split()
                                day = int(day_str)
                                month = BG_MONTHS[month_str]
                                date = datetime(datetime.now().year, month, day)
                            except (ValueError, KeyError):
                                logger.warning("devbg unparseable date", date_str=date_str)
                                continue

                            if date > cutoff:
                                filtered.append(card)

                    for card in filtered:
                        title_el = card.select_one("h6.job-title")
                        company_el = card.select_one("span.company-name")
                        url_el = card.select_one("a.overlay-link")
                        location_el = card.select_one("span.badge")

                        if not title_el or not company_el or not url_el:
                            continue

                        title = title_el.get_text(strip=True)
                        if not title_allowed(title, filters):
                            continue
                        company = company_el.get_text(strip=True)
                        url = str(url_el["href"])
                        location_text = (
                            location_el.get_text(separator=" ", strip=True).split()[0]
                            if location_el
                            else None
                        )
                        location = (
                            None
                            if location_text and location_text.lower() in {"fully", "remote"}
                            else location_text
                        )

                        detail_response = await client.get(url)
                        detail_response.raise_for_status()
                        detail_soup = BeautifulSoup(detail_response.text, "html.parser")

                        description_el = detail_soup.select_one("div.job_description")
                        description = (
                            description_el.get_text(separator=" ", strip=True)
                            if description_el
                            else None
                        )

                        job_result = RawJob(
                            title=title,
                            company=company,
                            location=location,
                            url=url,
                            source="dev.bg",
                            description=description,
                            raw_html=None,
                        )
                        result.append(job_result)
                        await sleep(1)

                    page += 1
                    await sleep(1)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        logger.info("devbg last page reached", page=page - 1)
                    else:
                        logger.exception("devbg fetch failed", page=page)
                    break
                except Exception:
                    logger.exception("devbg fetch failed", page=page)
                    break

        logger.info("devbg fetch completed", job_count=len(result))
        return result

    def source_name(self) -> str:
        return "dev.bg"
