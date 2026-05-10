"""CMS DKAN Provider Data API client.

All CMS API calls in this codebase must go through this module
(coding-conventions.md: module boundary; cms-api.md: client conventions).
No other module is permitted to import `requests` directly to call
data.cms.gov endpoints.

Two endpoint families are supported:

1. **Datastore query** — `/datastore/query/{dataset_id}/0`
   Used to fetch row data for a dataset. Supports pagination.

2. **Metastore** — `/metastore/schemas/dataset/items/{dataset_id}`
   and `/metastore/schemas/dataset/items` — used for dataset metadata,
   including `modified` (last publication timestamp), `released`,
   and `distribution[].downloadURL` (CSV archive link).

The metastore endpoints power refresh detection (scripts/detect_cms_refresh.py)
without bulk-downloading row data.

Note: row-data ingest in the live pipeline currently flows from CSV archives
(pipeline/ingest/csv_reader.py per DEC-027). This client is the DKAN entry point
for metadata polling and any future direct API ingest.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote

import requests

from pipeline.config import CMS_API_BASE_URL

logger = logging.getLogger(__name__)


# DKAN metastore base — derived from the same provider-data API root.
# data.cms.gov/provider-data/api/1/datastore/query → swap "datastore/query"
# for "metastore/schemas/dataset/items".
_DATASTORE_PREFIX = "/datastore/query"
_METASTORE_BASE = CMS_API_BASE_URL.replace(_DATASTORE_PREFIX, "/metastore/schemas/dataset/items")
_SEARCH_BASE = CMS_API_BASE_URL.replace(_DATASTORE_PREFIX, "/search")

USER_AGENT = "openchart-health-pipeline/0.1 (CMS Provider Data refresh detection)"
DEFAULT_TIMEOUT = 30.0
MAX_RETRIES = 5
PAGE_SIZE = 1500  # CMS PDC FAQ confirms max batch is 1500 (phase_0_findings.md W-NH-5)


class CMSAPIError(RuntimeError):
    """Raised when the CMS API returns a non-recoverable error."""


def _request_with_retry(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
) -> dict[str, Any]:
    """GET with exponential backoff on 5xx responses (cms-api.md).

    4xx responses are not retried (they indicate a bad request or a missing
    dataset, not transient infrastructure failure).

    Returns the parsed JSON body on success.
    Raises CMSAPIError on permanent failure (after retries exhausted, or on 4xx).
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_exc = exc
            delay = 2 ** (attempt - 1)
            logger.warning(
                "CMS API network error on attempt %d/%d for %s: %s. Retrying in %ds.",
                attempt, max_retries, url, exc, delay,
            )
            time.sleep(delay)
            continue

        if response.status_code >= 500:
            delay = 2 ** (attempt - 1)
            logger.warning(
                "CMS API 5xx on attempt %d/%d for %s: status=%d. Retrying in %ds.",
                attempt, max_retries, url, response.status_code, delay,
            )
            time.sleep(delay)
            continue

        if response.status_code >= 400:
            # 4xx — not retryable. Surface with full context (Rule 6).
            raise CMSAPIError(
                f"CMS API {response.status_code} for {url}: {response.text[:500]}"
            )

        try:
            return response.json()  # type: ignore[no-any-return]
        except ValueError as exc:
            raise CMSAPIError(
                f"CMS API returned non-JSON for {url}: {exc}; body={response.text[:200]}"
            ) from exc

    raise CMSAPIError(
        f"CMS API exhausted {max_retries} retries for {url}: {last_exc}"
    )


def get_dataset_metadata(dataset_id: str) -> dict[str, Any]:
    """Return the DKAN metastore record for a dataset.

    The record contains identifier, title, description, modified, released,
    and `distribution` (array of file links — CSV archives).

    `modified` is the publication timestamp we use to detect new vintages.

    Raises CMSAPIError if the dataset is not found or the API errors.
    """
    url = f"{_METASTORE_BASE}/{quote(dataset_id, safe='')}"
    data = _request_with_retry(url)
    if not isinstance(data, dict):
        raise CMSAPIError(f"Unexpected metastore response shape for {dataset_id}: {type(data)}")
    return data


def list_datasets(theme: str | None = None) -> list[dict[str, Any]]:
    """List all datasets in the Provider Data Catalog, optionally filtered by theme.

    Themes confirmed in phase_0_findings.md:
    - "Hospitals"
    - "Nursing homes including rehab services"
    """
    if theme:
        url = _SEARCH_BASE
        data = _request_with_retry(url, params={"theme": theme})
        results = data.get("results", {}) if isinstance(data, dict) else {}
        if isinstance(results, dict):
            return list(results.values())
        if isinstance(results, list):
            return results
        return []

    data = _request_with_retry(_METASTORE_BASE)
    if isinstance(data, list):
        return data
    return []


def fetch_dataset_rows(
    dataset_id: str,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch rows from the DKAN datastore query endpoint.

    Returns (rows, total). When `limit` is None, paginates through the entire
    dataset using PAGE_SIZE. When `limit` is set, returns at most that many
    rows starting at `offset` (one request).

    Per cms-api.md: paginates until `total` reached. User-Agent always set.
    Per Rule 6: failures raise with full context, no silent failure.
    """
    base = f"{CMS_API_BASE_URL}/{quote(dataset_id, safe='')}/0"

    if limit is not None:
        params = {"offset": offset, "limit": limit, "results": "true", "count": "true"}
        data = _request_with_retry(base, params=params)
        rows = list(data.get("results") or [])
        total_raw = data.get("count")
        try:
            total = int(total_raw) if total_raw is not None else len(rows)
        except (TypeError, ValueError):
            total = len(rows)
        return rows, total

    # Full pagination
    all_rows: list[dict[str, Any]] = []
    page_offset = offset
    total = 0
    while True:
        params = {
            "offset": page_offset,
            "limit": PAGE_SIZE,
            "results": "true",
            "count": "true",
        }
        data = _request_with_retry(base, params=params)
        page = list(data.get("results") or [])
        if not total:
            try:
                total = int(data.get("count") or 0)
            except (TypeError, ValueError):
                total = 0
        all_rows.extend(page)
        if not page or (total and len(all_rows) + offset >= total):
            break
        page_offset += len(page)
    return all_rows, total or len(all_rows)
