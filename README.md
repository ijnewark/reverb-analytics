# reverb-analytics

Python scraper that analyses Reverb sold listings by model using fuzzy string matching to identify underpriced and miscategorised gear listings.

## Overview

This tool uses the [Reverb public API](https://reverb.com/page/integrations) to:

1. **Fetch sold listings** for any search query
2. **Normalise model names** using fuzzy string matching (`rapidfuzz`), so "Gibson LP Standard", "gibson les paul std", and "LP Std - Gibson" all map to the same canonical model
3. **Flag underpriced listings** using z-scores against per-model price distributions
4. **Detect miscategorised listings** by comparing the listing's category against the expected category for its model

## Installation

```bash
git clone https://github.com/ijnewark/reverb-analytics.git
cd reverb-analytics
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

## Example Output

```
Fetching sold listings for 'Gibson Les Paul'...
  Page 1: fetched 50 listings (total: 50)
  Page 2: fetched 50 listings (total: 100)
  Page 3: fetched 50 listings (total: 150)
  No next page. Stopping.
Done. Total listings fetched: 150

Loaded 150 total listings from database.
Computed price stats for 6 (model, condition) groups.

======================================================================
FLAGGED DEALS
======================================================================
Total flagged: 8
  Underpriced: 6
  Miscategorised: 2
======================================================================

[UNDERPRICED] Gibson Les Paul Standard 2019 Bourbon Burst w/...
  Model: Gibson Les Paul Standard | Condition: Excellent
  Price: USD 1450.00 | z-score: -2.14
  URL: https://reverb.com/item/12345678

[UNDERPRICED,MISCATEGORISED] Gibson LP Std Traditional 2017 ...
  Model: Gibson Les Paul Standard | Condition: Good
  Price: USD 1100.00 | z-score: -1.87
  URL: https://reverb.com/item/23456789

[UNDERPRICED] Gibson Les Paul Standard 50s Gold Top - Mint C...
  Model: Gibson Les Paul Standard | Condition: Mint
  Price: USD 1875.00 | z-score: -1.76
  URL: https://reverb.com/item/34567890
```

## Future Scope: Secondary Marketplaces

While currently focused on Reverb, the architecture of this project can be extended to other secondary marketplace APIs to create a unified gear-valuation tool.

### eBay Integration
The [eBay Buy APIs](https://developer.ebay.com/api-docs/buy/static/main.html) (specifically the Browse API) provide access to completed and sold items. Integrating eBay would significantly increase the dataset size for computing price statistics.

**Potential Challenges:**
- **Authentication:** eBay uses OAuth 2.0, requiring a more complex header setup than Reverb.
- **Categorisation:** eBay's category tree is much deeper and would require a more robust `MODEL_CATEGORY_MAP`.
- **Filtering:** eBay's "Sold" state is managed via `fieldgroups=MATCHING_ITEMS` and specific item filters.

### Implementation Strategy
To support multiple marketplaces, the scraper could be refactored into a base class with marketplace-specific implementations (e.g., `ReverbScraper`, `EbayScraper`), allowing the core analysis and storage logic to remain platform-agnostic.

## How It Works

### 1. Data Collection
Fetches sold listings via `GET /api/listings?state=sold&query=<MODEL>` from the Reverb API. Results are stored in a local SQLite database (`data/reverb_listings.db`) to avoid re-fetching on subsequent runs.

### 2. Model Normalisation (Fuzzy Matching)
Listing titles on Reverb are notoriously inconsistent. This tool uses `rapidfuzz.token_sort_ratio` to map each title to a canonical model name.

## License
MIT
