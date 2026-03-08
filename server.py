"""
Zerochan MCP Server
Provides tools for searching and browsing Zerochan's anime image board via its read-only API.
"""

import json
import os
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from enum import Enum

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

ZEROCHAN_BASE_URL = "https://www.zerochan.net"
ZEROCHAN_USERNAME = os.environ.get("ZEROCHAN_USERNAME", "")
RATE_LIMIT_NOTE = "Zerochan enforces 60 requests/minute. Exceeding this may result in a temporary ban."
DEFAULT_LIMIT = 20
MAX_LIMIT = 250

# ─────────────────────────────────────────────
# Server Init
# ─────────────────────────────────────────────

mcp = FastMCP("zerochan_mcp")

# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class SortOrder(str, Enum):
    RECENT = "id"
    POPULAR = "fav"

class TimeRange(str, Enum):
    ALL_TIME = "0"
    LAST_7000 = "1"
    LAST_15000 = "2"

class Dimensions(str, Enum):
    LARGE = "large"
    HUGE = "huge"
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    SQUARE = "square"

class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"

# ─────────────────────────────────────────────
# Shared HTTP Client Helper
# ─────────────────────────────────────────────

async def zerochan_get(path: str, params: dict) -> dict:
    """
    Perform a GET request to the Zerochan API.

    Args:
        path: URL path (e.g. '/Hatsune+Miku')
        params: Query string parameters (json=True always included)

    Returns:
        Parsed JSON response dict

    Raises:
        ValueError: If ZEROCHAN_USERNAME env var is not set
        httpx.HTTPStatusError: On non-2xx responses
        httpx.TimeoutException: On request timeout
    """
    if not ZEROCHAN_USERNAME:
        raise ValueError(
            "ZEROCHAN_USERNAME is not set. Add it to your MCP config: "
            '"env": {"ZEROCHAN_USERNAME": "YourUsername"}'
        )
    params["json"] = True
    url = f"{ZEROCHAN_BASE_URL}{path}"
    user_agent = f"zerochan-mcp - {ZEROCHAN_USERNAME}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params, headers={"User-Agent": user_agent})
        response.raise_for_status()
        return response.json()


def handle_api_error(e: Exception) -> str:
    """Return a consistent, actionable error message."""
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 403:
            return "Error 403: Access denied. Ensure you provide a valid Zerochan username. Anonymous requests may be banned."
        if code == 404:
            return "Error 404: Resource not found. Check that the tag or entry ID exists on Zerochan."
        if code == 429:
            return f"Error 429: Rate limit hit. {RATE_LIMIT_NOTE}"
        return f"Error {code}: API request failed — {e.response.text[:200]}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Zerochan may be slow or unavailable. Try again shortly."
    if isinstance(e, ValueError):
        return f"Error: Could not parse Zerochan's response as JSON. {str(e)}"
    return f"Error: Unexpected error — {type(e).__name__}: {str(e)}"


# ─────────────────────────────────────────────
# Formatting Helpers
# ─────────────────────────────────────────────

def format_post_list_markdown(items: list, source: str) -> str:
    """Format a list of post summaries as a Markdown table."""
    if not items:
        return "No results found."

    lines = [f"### Zerochan Results from `{source}`\n"]
    lines.append(f"| ID | Tags | Dimensions | Favorites | Full Image |")
    lines.append(f"|---|---|---|---|---|")

    for item in items:
        entry_id = item.get("id", "N/A")
        tags = ", ".join(item.get("tags", [])[:5])
        if len(item.get("tags", [])) > 5:
            tags += f" (+{len(item['tags']) - 5} more)"
        width = item.get("width", "?")
        height = item.get("height", "?")
        fav = item.get("fav", "?")
        full_url = item.get("full", f"https://www.zerochan.net/{entry_id}")
        lines.append(f"| [{entry_id}]({full_url}) | {tags} | {width}×{height} | {fav} | [View]({full_url}) |")

    return "\n".join(lines)


def format_post_detail_markdown(data: dict) -> str:
    """Format a single post's detailed data as Markdown."""
    entry_id = data.get("id", "N/A")
    tags = data.get("tags", [])
    source = data.get("source", "N/A")
    width = data.get("width", "?")
    height = data.get("height", "?")
    fav = data.get("fav", 0)
    full_url = data.get("full", f"https://www.zerochan.net/{entry_id}")
    medium_url = data.get("medium", "")
    small_url = data.get("small", "")
    primary_tag = data.get("primary", "N/A")
    anime = data.get("anime", None)
    manga = data.get("manga", None)
    game = data.get("game", None)

    lines = [
        f"## Zerochan Entry #{entry_id}",
        f"",
        f"**Primary Tag:** {primary_tag}",
        f"**Dimensions:** {width} × {height}",
        f"**Favorites:** {fav}",
        f"**Source:** {source}",
        f"",
        f"**Tags ({len(tags)}):** {', '.join(tags)}",
    ]

    if anime:
        lines.append(f"**Anime:** {anime}")
    if manga:
        lines.append(f"**Manga:** {manga}")
    if game:
        lines.append(f"**Game:** {game}")

    lines += [
        f"",
        f"**Full Image:** {full_url}",
    ]
    if medium_url:
        lines.append(f"**Medium Preview:** {medium_url}")
    if small_url:
        lines.append(f"**Small Preview:** {small_url}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# Input Models
# ─────────────────────────────────────────────

class BrowseAllInput(BaseModel):
    """Input for browsing all Zerochan entries."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    page: int = Field(default=1, description="Page number for pagination (starts at 1)", ge=1)
    limit: int = Field(default=DEFAULT_LIMIT, description="Number of results per page (1–250)", ge=1, le=MAX_LIMIT)
    sort: SortOrder = Field(default=SortOrder.RECENT, description="Sort order: 'id' = most recent, 'fav' = most popular")
    time_range: Optional[TimeRange] = Field(default=None, description="Time range for popularity sort: '0' = all time, '1' = last 7000 entries, '2' = last 15000 entries")
    dimensions: Optional[Dimensions] = Field(default=None, description="Filter by image dimensions: large, huge, landscape, portrait, square")
    color: Optional[str] = Field(default=None, description="Filter by dominant color, e.g. 'red', 'blue', 'green'", max_length=32)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


class SearchByTagInput(BaseModel):
    """Input for searching Zerochan entries by one or more tags."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    tags: list[str] = Field(
        ...,
        description="One or more tags to filter by (e.g. ['Hatsune Miku'] or ['Hatsune Miku', 'Flower']). Tags are joined with commas in the URL.",
        min_length=1
    )
    strict: bool = Field(
        default=False,
        description="If True, use strict mode — only returns entries where the FIRST tag is the primary tag. Only works with a single tag."
    )
    page: int = Field(default=1, description="Page number for pagination", ge=1)
    limit: int = Field(default=DEFAULT_LIMIT, description="Number of results per page (1–250)", ge=1, le=MAX_LIMIT)
    sort: SortOrder = Field(default=SortOrder.RECENT, description="Sort order: 'id' = most recent, 'fav' = most popular")
    dimensions: Optional[Dimensions] = Field(default=None, description="Filter by image dimensions: large, huge, landscape, portrait, square")
    color: Optional[str] = Field(default=None, description="Filter by dominant color, e.g. 'red', 'blue', 'green'", max_length=32)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        cleaned = [t.strip() for t in v if t.strip()]
        if not cleaned:
            raise ValueError("At least one non-empty tag is required.")
        return cleaned


class GetEntryInput(BaseModel):
    """Input for retrieving a single Zerochan entry by ID."""
    model_config = ConfigDict(extra="forbid")

    entry_id: int = Field(
        ...,
        description="The numeric Zerochan entry ID (visible in the URL of any post). e.g. 3793685",
        ge=1
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


# ─────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────

@mcp.tool(
    name="zerochan_browse",
    annotations={
        "title": "Browse All Zerochan Entries",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def zerochan_browse(params: BrowseAllInput) -> str:
    """Browse all Zerochan entries with optional filtering and pagination.

    Queries the Zerochan global feed without any tag filter. Supports sorting by
    recency or popularity, filtering by dimensions or color, and pagination.

    Args:
        params (BrowseAllInput): Input parameters including:
            - username (str): Your Zerochan username for the User-Agent header (required)
            - page (int): Page number (default: 1)
            - limit (int): Results per page, 1–250 (default: 20)
            - sort (SortOrder): 'id' for recent, 'fav' for popular (default: 'id')
            - time_range (Optional[TimeRange]): '0' all-time, '1' last 7000, '2' last 15000
            - dimensions (Optional[Dimensions]): Filter by image shape
            - color (Optional[str]): Filter by dominant color name
            - response_format (ResponseFormat): 'markdown' or 'json' (default: 'markdown')

    Returns:
        str: Paginated list of entries in the requested format.
             Markdown: formatted table with ID, tags, dimensions, favorites, links.
             JSON: raw API response with all fields.
    """
    query: dict = {
        "p": params.page,
        "l": params.limit,
        "s": params.sort.value,
    }
    if params.time_range is not None:
        query["t"] = params.time_range.value
    if params.dimensions is not None:
        query["d"] = params.dimensions.value
    if params.color:
        query["c"] = params.color

    try:
        data = await zerochan_get("/", query)
    except Exception as e:
        return handle_api_error(e)

    items = data.get("items", data) if isinstance(data, dict) else data

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, ensure_ascii=False)

    return format_post_list_markdown(items if isinstance(items, list) else [], "Global Feed")


@mcp.tool(
    name="zerochan_search",
    annotations={
        "title": "Search Zerochan by Tag(s)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def zerochan_search(params: SearchByTagInput) -> str:
    """Search Zerochan entries by one or more tags.

    Supports single-tag, multi-tag, and strict-mode queries. Zerochan tag names
    use Title Case with spaces (e.g. 'Hatsune Miku', not 'hatsune_miku').

    Multi-tag example: tags=['Hatsune Miku', 'Flower'] → /Hatsune+Miku,Flower?json
    Strict mode: tags=['Rem'] + strict=True → /Rem?json&strict (only entries where Rem is primary tag)

    Note: Strict mode only works with a single tag. Passing multiple tags with strict=True
    will ignore the strict flag.

    Args:
        params (SearchByTagInput): Input parameters including:
            - username (str): Your Zerochan username (required)
            - tags (list[str]): One or more tag names (Title Case preferred)
            - strict (bool): If True and single tag, use strict mode (default: False)
            - page (int): Page number (default: 1)
            - limit (int): Results per page, 1–250 (default: 20)
            - sort (SortOrder): 'id' for recent, 'fav' for popular (default: 'id')
            - dimensions (Optional[Dimensions]): Filter by image shape
            - color (Optional[str]): Filter by dominant color name
            - response_format (ResponseFormat): 'markdown' or 'json' (default: 'markdown')

    Returns:
        str: Matching entries in the requested format.
             Markdown: formatted table with ID, tags, dimensions, favorites, links.
             JSON: raw API response with all available fields.
    """
    # Build URL path: tags are joined with commas, spaces replaced with +
    encoded_tags = [t.replace(" ", "+") for t in params.tags]
    tag_path = ",".join(encoded_tags)
    path = f"/{tag_path}"

    query: dict = {
        "p": params.page,
        "l": params.limit,
        "s": params.sort.value,
    }
    if params.dimensions is not None:
        query["d"] = params.dimensions.value
    if params.color:
        query["c"] = params.color

    # Strict mode only works with a single tag
    use_strict = params.strict and len(params.tags) == 1
    if use_strict:
        query["strict"] = True

    try:
        data = await zerochan_get(path, query)
    except Exception as e:
        return handle_api_error(e)

    items = data.get("items", data) if isinstance(data, dict) else data
    source = " + ".join(params.tags) + (" [strict]" if use_strict else "")

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, ensure_ascii=False)

    return format_post_list_markdown(items if isinstance(items, list) else [], source)


@mcp.tool(
    name="zerochan_get_entry",
    annotations={
        "title": "Get Zerochan Entry Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def zerochan_get_entry(params: GetEntryInput) -> str:
    """Retrieve detailed information about a single Zerochan entry by its numeric ID.

    Returns full metadata including all tags, image URLs (full/medium/small),
    source, dimensions, favorites, and associated anime/manga/game categories.

    Args:
        params (GetEntryInput): Input parameters including:
            - username (str): Your Zerochan username (required)
            - entry_id (int): Numeric ID of the Zerochan post (e.g. 3793685)
            - response_format (ResponseFormat): 'markdown' or 'json' (default: 'markdown')

    Returns:
        str: Detailed entry data in the requested format.
             Markdown: formatted card with all metadata, tag list, and image URLs.
             JSON: complete raw API response with all available fields.

    Schema (JSON):
        {
            "id": int,
            "primary": str,           # Primary/main tag for this image
            "tags": list[str],         # All associated tags
            "width": int,
            "height": int,
            "fav": int,                # Favorite/popularity count
            "source": str,             # Original source URL if available
            "full": str,               # Direct URL to full resolution image
            "medium": str,             # Medium preview URL
            "small": str,              # Small thumbnail URL
            "anime": str | null,       # Associated anime title if any
            "manga": str | null,
            "game": str | null
        }
    """
    try:
        data = await zerochan_get(f"/{params.entry_id}", {})
    except Exception as e:
        return handle_api_error(e)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, ensure_ascii=False)

    return format_post_detail_markdown(data)


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

def main():
    """Entry point for PyPI script installation (zerochan-mcp command)."""
    mcp.run()


if __name__ == "__main__":
    main()
