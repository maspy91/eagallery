"""Shared helpers for the admin CSV export endpoints (photos, videos,
comments, conversations, customers) -- one place for date-range query
param parsing and CSV response building, instead of five copies of the
same csv.writer/StreamingResponse boilerplate."""

import csv
import io
from collections.abc import Iterable
from datetime import date, datetime, time, timezone

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

# Hard ceiling on rows returned by any export endpoint -- this is meant
# for "download today's/this week's activity as a spreadsheet", not
# unbounded data dumps. Comfortably past any realistic size for this
# business today; revisit with real pagination/streaming from the DB
# if a table ever legitimately needs more rows exported than this.
EXPORT_ROW_LIMIT = 5000


def parse_date_range(date_from: str | None, date_to: str | None) -> tuple[datetime | None, datetime | None]:
    """Parses 'YYYY-MM-DD' query params into an inclusive UTC datetime
    range. date_to is bumped to 23:59:59.999999 that day so passing the
    same date as both date_from and date_to captures the whole day, not
    just the instant at midnight."""

    def _parse(value: str | None, *, end_of_day: bool) -> datetime | None:
        if not value:
            return None
        try:
            d = date.fromisoformat(value)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid date: {value!r} (expected YYYY-MM-DD)")
        return datetime.combine(d, time.max if end_of_day else time.min, tzinfo=timezone.utc)

    parsed_from = _parse(date_from, end_of_day=False)
    parsed_to = _parse(date_to, end_of_day=True)
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "date_from must not be after date_to")
    return parsed_from, parsed_to


def csv_response(filename: str, header: list[str], rows: Iterable[list[str]]) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
