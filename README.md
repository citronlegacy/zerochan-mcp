# zerochan-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-blueviolet)](https://modelcontextprotocol.io/)

A Python [MCP](https://modelcontextprotocol.io/) server wrapping the read-only [Zerochan](https://www.zerochan.net) anime image board API. Connect it to Claude Desktop, Cursor, or any MCP-compatible AI assistant to browse, search, and inspect one of the web's most comprehensively tagged anime image collections — directly from a conversation.

Built as a sister server to [gelbooru-mcp](https://github.com/citronlegacy/gelbooru-mcp) and designed to be one piece of a future **MultiBoru** federated image board MCP.

---

## ✨ Features

- **Browse** the global Zerochan feed — sort by newest or most-favorited, filter by dimensions or dominant color
- **Search** by one or more tags simultaneously using Zerochan's natural Title Case format (`Hatsune Miku`, not `hatsune_miku`)
- **Strict mode** — narrow results to entries where a specific tag is the *primary* subject, cutting group shots and incidental appearances
- **Full entry details** — all tags, full/medium/small image URLs, source, dimensions, favorites, and anime/manga/game associations
- Returns results as a clean **Markdown table** or raw **JSON** — your choice
- Fully **Pydantic-validated** inputs with enum constraints and custom tag validators
- Clear, actionable **error messages** for rate limits, auth failures, and timeouts

---

## 📦 Installation

### Prerequisites

- Python 3.10+
- `git`

### Quick Start

```bash
git clone https://github.com/citronlegacy/zerochan-mcp.git
cd zerochan-mcp
chmod +x setup.sh && ./setup.sh
```

Or without chmod:

```bash
bash setup.sh
```

### Manual Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 🔑 Authentication

Zerochan requires a valid **username** in every request's User-Agent header. Unauthenticated requests are blocked.

```bash
export ZEROCHAN_USERNAME="YourZerochanUsername"
```

> Your username is included in the User-Agent string as `zerochan-mcp - YourUsername`, exactly as Zerochan's API requires. The server validates this on every call and returns a clear error message if it is missing — no silent failures.

---

## ▶️ Running the Server

```bash
# via the venv created by setup.sh:
.venv/bin/python server.py

# or with the venv activated:
source .venv/bin/activate
python server.py
```

---

## ⚙️ Configuration

### Claude Desktop

Add the following to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zerochan-mcp": {
      "command": "/absolute/path/to/zerochan-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/zerochan-mcp/server.py"],
      "env": {
        "ZEROCHAN_USERNAME": "YourZerochanUsername"
      }
    }
  }
}
```

### VS Code / Cursor / Other MCP Clients

Configure according to your client's documentation:

- **Command:** `/absolute/path/to/zerochan-mcp/.venv/bin/python`
- **Args:** `/absolute/path/to/zerochan-mcp/server.py`
- **Transport:** stdio
- **Env:** `ZEROCHAN_USERNAME=YourZerochanUsername`

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector .venv/bin/python server.py
```

---

## 💡 Usage Examples

### Browse the latest anime art

> "Show me the 10 most recent images on Zerochan."

The LLM calls `zerochan_browse` with `limit: 10, sort: "id"` and returns a paginated Markdown table of the newest uploads — IDs, tags, dimensions, and direct links.

---

### Find the all-time most favorited images

> "What are the most popular images on Zerochan of all time?"

The LLM calls `zerochan_browse` with `sort: "fav", time_range: "0"` and returns the highest-favorited entries globally.

---

### Search for a character

> "Find me portrait-mode images of Hatsune Miku."

The LLM calls `zerochan_search` with `tags: ["Hatsune Miku"], dimensions: "portrait"`. No tag normalization required — Zerochan's Title Case maps almost one-to-one with how people naturally write character names.

---

### Multi-tag search — character + theme

> "Show me Rem from Re:Zero with an umbrella."

The LLM calls `zerochan_search` with `tags: ["Rem", "Umbrella"]`. Zerochan joins them as `/Rem,Umbrella?json` internally, returning only images tagged with **both** simultaneously.

---

### Strict mode — images where a character is the main subject

> "I only want images where Hatsune Miku is the actual primary subject, not just tagged."

The LLM calls `zerochan_search` with `tags: ["Hatsune Miku"], strict: true`. This filters to entries where Hatsune Miku is the **primary tag**, removing group shots and background appearances.

---

### Get full metadata for a specific post

> "Give me all the details on Zerochan entry 3793685 — tags, source, full image URL."

The LLM calls `zerochan_get_entry` with `entry_id: 3793685` and returns a complete metadata card: every tag, full/medium/small image URLs, source, dimensions, favorites, and associated anime/game/manga categories.

---

### Raw JSON for downstream processing

> "Search for Yotsuba images and give me the raw JSON."

The LLM calls `zerochan_search` with `tags: ["Yotsuba"], response_format: "json"` and returns the unprocessed Zerochan API payload ready for further processing.

---

## 🛠️ Available Tools

| Tool | Description | Key Parameters |
|---|---|---|
| `zerochan_browse` | Browse the global Zerochan feed | `page`, `limit`, `sort`, `time_range`, `dimensions`, `color` |
| `zerochan_search` | Search entries by one or more tags | `tags`, `strict`, `page`, `limit`, `sort`, `dimensions`, `color` |
| `zerochan_get_entry` | Get full metadata for a single entry by ID | `entry_id` |

All tools accept `response_format: "markdown"` (default) or `"json"`.

---

## 📖 Tools Reference

### `zerochan_browse`

Browse all Zerochan entries with optional filtering and pagination. No tag required — queries the full global feed.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `page` | int | ❌ | 1 | Page number (starts at 1) |
| `limit` | int | ❌ | 20 | Results per page (1–250) |
| `sort` | enum | ❌ | `id` | `id` = newest first, `fav` = most favorited |
| `time_range` | enum | ❌ | — | `0` = all time, `1` = last 7 000 entries, `2` = last 15 000 entries |
| `dimensions` | enum | ❌ | — | `large`, `huge`, `landscape`, `portrait`, `square` |
| `color` | str | ❌ | — | Dominant color name, e.g. `blue`, `red`, `pink` |
| `response_format` | enum | ❌ | `markdown` | `markdown` or `json` |

**Example response**

```
### Zerochan Results from `Global Feed`

| ID | Tags | Dimensions | Favorites | Full Image |
|---|---|---|---|---|
| 4666171 | Female, Twin Tails, Flower, Hatsune Miku, Music (+33 more) | 1000×1500 | ? | View |
```

---

### `zerochan_search`

Search Zerochan entries by one or more tags. Tags use Zerochan's Title Case with spaces format.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `tags` | list[str] | ✅ | — | One or more tags, e.g. `["Hatsune Miku"]` or `["Rem", "Umbrella"]` |
| `strict` | bool | ❌ | false | Restrict to entries where the **first** tag is the primary tag (single-tag only) |
| `page` | int | ❌ | 1 | Page number |
| `limit` | int | ❌ | 20 | Results per page (1–250) |
| `sort` | enum | ❌ | `id` | `id` = newest, `fav` = most favorited |
| `dimensions` | enum | ❌ | — | `large`, `huge`, `landscape`, `portrait`, `square` |
| `color` | str | ❌ | — | Dominant color filter |
| `response_format` | enum | ❌ | `markdown` | `markdown` or `json` |

> **Tag format:** Zerochan uses Title Case with spaces — `Hatsune Miku` not `hatsune_miku`. Natural-language character names work verbatim in most cases.

> **Multi-tag:** `tags: ["Hatsune Miku", "Flower"]` → `/Hatsune+Miku,Flower?json`

> **Strict mode:** Only works with a single tag. Silently ignored when multiple tags are provided.

---

### `zerochan_get_entry`

Retrieve complete metadata for a single Zerochan post by its numeric ID.

**Parameters**

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `entry_id` | int | ✅ | — | Numeric post ID, e.g. `3793685` (visible in the post URL) |
| `response_format` | enum | ❌ | `markdown` | `markdown` or `json` |

**Example response (markdown)**

```
## Zerochan Entry #3793685

**Primary Tag:** Hatsune Miku
**Dimensions:** 1748 × 2480
**Favorites:** 42
**Source:** https://...
**Tags (28):** Hatsune Miku, VOCALOID, Female, Twin Tails, ...

**Full Image:** https://static.zerochan.net/...
**Medium Preview:** https://static.zerochan.net/...
```

**Response schema (JSON)**

```json
{
  "id": 3793685,
  "primary": "Hatsune Miku",
  "tags": ["Hatsune Miku", "VOCALOID", "Female", "..."],
  "width": 1748,
  "height": 2480,
  "fav": 42,
  "source": "https://...",
  "full": "https://static.zerochan.net/...",
  "medium": "https://static.zerochan.net/...",
  "small": "https://static.zerochan.net/...",
  "anime": "VOCALOID",
  "manga": null,
  "game": null
}
```

---

## 🤖 Notes for LLMs

- **Tag format:** Zerochan uses Title Case with spaces — `Hatsune Miku`, `Rem`, `Attack On Titan`. Unlike Gelbooru/Danbooru, natural-language names map directly to Zerochan tags in most cases.
- **Strict mode:** Use it when the user asks specifically for images *of* a character, not just images *featuring* them. Only valid with a single tag.
- **Multi-tag search:** Each entry must match **all** tags. Use for character + theme combos (`["Rem", "Rain"]`, `["Naruto", "Ramen"]`).
- **Pagination:** `zerochan_browse` and `zerochan_search` return up to 250 results per call. Use `page` to paginate through up to 100 pages (20 000 entries) per tag.
- **Rate limit:** 60 requests/minute. Avoid tight loops; space calls when paginating deeply.
- **Entry IDs:** Visible in Zerochan URLs (`zerochan.net/3793685`). Pass them to `zerochan_get_entry` to resolve full metadata.

---

## ⚠️ Known Limitations

- **Rate limit:** 60 requests/minute enforced server-side. Exceeding this may trigger a temporary ban.
- **Username required:** Every request must carry a valid Zerochan username in the User-Agent. The server validates this and returns a clear error if missing.
- **Strict mode + multi-tag:** Strict mode is silently ignored when more than one tag is provided — Zerochan API limitation.
- **No write access:** Zerochan's public API is fully read-only. Uploading, favoriting, and commenting are not supported.
- **No tag autocomplete:** Zerochan does not expose a tag search/autocomplete endpoint in the JSON API. Use the website for tag discovery when needed.

---

## 🐛 Troubleshooting

**`ZEROCHAN_USERNAME is not set`**
- Add it to your client's `"env"` block, or: `export ZEROCHAN_USERNAME="YourUsername"`

**Error 403 — Access denied**
- Ensure your Zerochan username is correct and your account is in good standing.
- Blank or missing User-Agent strings are rejected by Zerochan.

**Error 429 — Rate limit**
- Wait 60 seconds and retry. Avoid paginating in rapid loops.

**Error 404 — Not found**
- The tag or entry ID does not exist on Zerochan. Check spelling; entry IDs come from post URLs.

**Strict mode returns fewer results than expected**
- By design — strict mode returns only entries where the tag is the **primary** classification. Use non-strict for broader results.

---

## 🤝 Contributing

Pull requests are welcome! If you find an API edge case not handled, a tag format inconsistency, or want to add a new filter, open an issue or PR.

### Development Setup

```bash
git clone https://github.com/citronlegacy/zerochan-mcp.git
cd zerochan-mcp
bash setup.sh
source .venv/bin/activate
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🔗 Links

- 🌐 [Zerochan](https://www.zerochan.net)
- 🔧 [MCP documentation](https://modelcontextprotocol.io/)
- 🗂️ [MCP Registry](https://registry.modelcontextprotocol.io)
- 🔍 [Glama MCP Directory](https://glama.ai/mcp/servers)
- 🎨 [gelbooru-mcp](https://github.com/citronlegacy/gelbooru-mcp) — sister MCP server
- 🐛 [Bug Reports](https://github.com/citronlegacy/zerochan-mcp/issues)
- 💡 [Discussions](https://github.com/citronlegacy/zerochan-mcp/discussions)

---

## Relation to MultiBoru MCP

This server is one piece of a planned **MultiBoru** federated image board MCP that will aggregate Gelbooru, Danbooru, and Zerochan queries in parallel with cross-site tag normalization.

| Site | Max Tags | Tag Format | Auth |
|---|---|---|---|
| Gelbooru | Many | `snake_case` | Optional API key |
| Danbooru | 2 (free) / 6 (Gold) | `snake_case` | Optional |
| Zerochan | Many | `Title Case` | Username in User-Agent |
