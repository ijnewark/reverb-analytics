# reverb-deals-finder

Python scraper that analyses Reverb sold listings by model using fuzzy string matching to identify underpriced and miscategorised gear listings.

## Overview

This tool uses the [Reverb public API](https://reverb.com/page/integrations) to:

1. **Fetch sold listings** for any search query
2. **Normalise model names** using fuzzy string matching (`rapidfuzz`), so "Gibson LP Standard", "gibson les paul std", and "LP Std - Gibson" all map to the same canonical model
3. **Flag underpriced listings** using z-scores against per-model price distributions
4. **Detect miscategorised listings** by comparing the listing's category against the expected category for its model

## Installation

```bash
git clone https://github.com/ijnewark/reverb-deals-finder.git
cd reverb-deals-finder
pip install -r requirements.txt
```

## Quick Start

```bash
# Fetch and analyse a single model
python reverb_scraper.py --query "Gibson Les Paul" --pages 5

# Run all configured models
python reverb_scraper.py --all

# Export results to CSV
python reverb_scraper.py --query "Fender Stratocaster" --export
```

## Usage

```
usage: reverb_scraper.py [-h] [--query QUERY] [--pages PAGES]
                         [--all] [--export]

Scrape and analyse Reverb sold listings for deals.

options:
  -h, --help            show this help message and exit
  --query QUERY, -q QUERY
                        Single search query (e.g. "Gibson Les Paul")
  --pages PAGES, -p PAGES
                        Max pages to fetch per query (default: 20)
  --all, -a             Run all queries from config.SEARCH_QUERIES
  --export              Export results to CSV after analysis
```

## How It Works

### 1. Data Collection

Fetches sold listings via `GET /api/listings?state=sold&query=<MODEL>` from the Reverb API. Results are stored in a local SQLite database (`data/reverb_listings.db`) to avoid re-fetching on subsequent runs.

### 2. Model Normalisation (Fuzzy Matching)

Listing titles on Reverb are notoriously inconsistent. This tool uses `rapidfuzz.token_sort_ratio` to map each title to a canonical model name:

| Raw Title | Canonical Match |
|---|---|
| "Gibson LP Standard" | Gibson Les Paul Standard |
| "les paul std gibson" | Gibson Les Paul Standard |
| "Fender Strat 60s" | Fender Stratocaster |
| "PRS Custom 24 CE" | PRS Custom 24 |

### 3. Underpricing Detection

For each (model, condition) group, the tool computes the median price and standard deviation from all sold listings. Active or recent sold listings with a z-score below the configured threshold (default: -1.5) are flagged as underpriced.

### 4. Miscategorisation Detection

Each canonical model has an expected category (e.g. "Gibson Les Paul" -> "Electric Guitars"). If a listing's stated category doesn't fuzzy-match its expected category, it's flagged. This is useful because miscategorised items often get fewer views and can go cheaper.

## Configuration

Edit `config.py` to customise:

| Setting | Description |
|---|---|
| `SEARCH_QUERIES` | List of search terms to run with `--all` |
| `CANONICAL_MODELS` | Reference models for fuzzy matching |
| `FUZZY_MATCH_THRESHOLD` | Minimum score (0-100) to accept a model match (default: 70) |
| `Z_SCORE_THRESHOLD` | How far below the median to flag as underpriced (default: -1.5) |
| `API_DELAY_SECONDS` | Delay between API calls (default: 0.5) |
| `API_MAX_PAGES` | Max pages to fetch per query (default: 20) |

## Output

The console prints a summary of all flagged deals, including:

- Title and URL
- Canonical model and condition
- Price in GBP
- Z-score
- Flags (UNDERPRICED / MISCATEGORISED)

With `--export`, a full CSV of all listings is saved to `data/sold_listings.csv`.

## Limitations

- **Sold prices are asking prices**, not final transacted prices. Treat them as upper bounds.
- **History is capped at ~1 year** by Reverb. Start caching data now if you want long-term tracking.
- **API ToS** prohibits using the API for "analytics or machine learning" at scale. Fine for personal use.
- **No authentication** means limited field access (title, price, condition, category only).

## License

MIT License. See [LICENSE](LICENSE) for details.
