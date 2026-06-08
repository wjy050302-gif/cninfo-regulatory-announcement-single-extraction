from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable

import requests

from .utils import strip_em_tags


@dataclass(frozen=True)
class CninfoAnnouncement:
    doc_id: str
    stock_code: str
    stock_name: str
    market: str  # "szse" or "sse"
    announcement_title: str
    announcement_type: str | None
    publish_date: str  # YYYY-MM-DD
    announcement_time_ms: int
    adjunct_url: str | None
    pdf_url: str | None
    search_key: str


class CninfoClient:
    def __init__(
        self,
        endpoint: str,
        referer: str,
        user_agent: str = "Mozilla/5.0",
        timeout_seconds: int = 30,
    ):
        self.endpoint = endpoint
        self.referer = referer
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": self.referer,
        }

    def query(
        self,
        *,
        column: str,
        tabName: str,
        searchkey: str,
        seDate: str,
        page_num: int,
        page_size: int,
        sortName: str = "announcementTime",
        sortType: str = "desc",
        max_retries: int = 3,
        sleep_seconds: float = 0.0,
    ) -> dict[str, Any]:
        data = {
            "pageNum": page_num,
            "pageSize": page_size,
            "column": column,
            "tabName": tabName,
            "plate": "",
            "stock": "",
            "searchkey": searchkey,
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": seDate,
            "sortName": sortName,
            "sortType": sortType,
            "isHLtitle": "true",
        }

        last_err: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                r = requests.post(
                    self.endpoint,
                    headers=self._headers(),
                    data=data,
                    timeout=self.timeout_seconds,
                )
                # cninfo can return 504 sometimes; treat as retryable.
                if r.status_code in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"cninfo http {r.status_code}")
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
                if attempt >= max_retries:
                    break
                if sleep_seconds:
                    import time

                    time.sleep(sleep_seconds * attempt)
        assert last_err is not None
        raise last_err

    @staticmethod
    def _to_announcement(
        a: dict[str, Any], *, market: str, search_key: str
    ) -> CninfoAnnouncement | None:
        doc_id = (a.get("announcementId") or "").strip()
        if not doc_id:
            return None
        stock_code = (a.get("secCode") or "").strip()
        stock_name = (a.get("secName") or "").strip()
        title = strip_em_tags(a.get("announcementTitle") or "")
        ann_type = a.get("announcementType")
        ann_type = str(ann_type).strip() if ann_type is not None else None
        ts = a.get("announcementTime")
        try:
            ts_int = int(ts)
        except Exception:
            return None
        date = dt.datetime.utcfromtimestamp(ts_int / 1000).date().isoformat()
        adjunct = a.get("adjunctUrl")
        adjunct = adjunct.strip() if isinstance(adjunct, str) and adjunct.strip() else None
        pdf_url = f"http://static.cninfo.com.cn/{adjunct}" if adjunct else None

        return CninfoAnnouncement(
            doc_id=doc_id,
            stock_code=stock_code,
            stock_name=stock_name,
            market=market,
            announcement_title=title,
            announcement_type=ann_type,
            publish_date=date,
            announcement_time_ms=ts_int,
            adjunct_url=adjunct,
            pdf_url=pdf_url,
            search_key=search_key,
        )

    def iter_announcements(
        self,
        *,
        column: str,
        tabName: str,
        searchkey: str,
        seDate: str,
        page_size: int,
        max_pages: int = 200,
        max_retries: int = 3,
        sleep_seconds: float = 0.6,
    ) -> Iterable[CninfoAnnouncement]:
        for page_num in range(1, max_pages + 1):
            js = self.query(
                column=column,
                tabName=tabName,
                searchkey=searchkey,
                seDate=seDate,
                page_num=page_num,
                page_size=page_size,
                max_retries=max_retries,
                sleep_seconds=sleep_seconds,
            )
            anns = js.get("announcements") or []
            if not anns:
                return

            for a in anns:
                item = self._to_announcement(a, market=column, search_key=searchkey)
                if item is not None:
                    yield item

            # polite sleep between pages
            if sleep_seconds:
                import time

                time.sleep(sleep_seconds)
