"""
Reverb Deals Finder - Sold Listings Scraper and Analysis

Fetches sold listings from the Reverb API, normalises model names using
fuzzy string matching, and flags underpriced and miscategorised listings.

Usage:
    pip install -r requirements.txt
    python reverb_scraper.py --query "Gibson Les Paul" --pages 5
    python reverb_scraper.py --all          # Run all queries from config
"""

import argparse
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import httpx
import pandas as pd
from rapidfuzz import fuzz, process

import config


def setup_database(db_path: str) -> sqlite3.Connection:
    """Initialise the SQLite database and create tables."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sold_listings (
            id              INTEGER PRIMARY KEY,
            listing_id      INTEGER UNIQUE,
            title           TEXT,
            make            TEXT,
            model           TEXT,
            price_amount    REAL,
            price_currency  TEXT,
            condition_name  TEXT,
            category_full   TEXT,
            year            TEXT,
            url             TEXT,
            fetched_at      TEXT,
            canonical_model TEXT,
            fuzzy_score     REAL
        )
    """)
    conn.commit()
    return conn


def fetch_sold_listings(
    query: str,
    max_pages: int = config.API_MAX_PAGES,
) -> list[dict[str, Any]]:
    """
    Fetch sold listings from the Reverb API for a given search query.

    Args:
        query: Search term (e.g. "Gibson Les Paul")
        max_pages: Maximum number of pages to fetch

    Returns:
        List of listing dictionaries.
    """
    all_listings = []
    url = f"{config.REVERB_API_BASE}/listings"

    print(f"Fetching sold listings for '{query}'...")

    for page in range(1, max_pages + 1):
        params = {
            "query": query,
            "state": "sold",
            "per_page": config.API_PER_PAGE,
            "page": page,
        }
        try:
            r = httpx.get(url, params=params, headers=config.REVERB_API_HEADERS, timeout=10)
            if r.status_code == 429:
                print("  Rate limited (429). Waiting 5 seconds...")
                time.sleep(5)
                continue
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            print(f"  HTTP error on page {page}: {e}")
            break

        listings = data.get("listings", [])
        if not listings:
            print(f"  No more listings at page {page}. Stopping.")
            break

        all_listings.extend(listings)
        print(f"  Page {page}: fetched {len(listings)} listings (total: {len(all_listings)})")

        # Check for next page link
        links = data.get("_links", {})
        if "next" not in links:
            print("  No next page. Stopping.")
            break

        time.sleep(config.API_DELAY_SECONDS)

    print(f"Done. Total listings fetched: {len(all_listings)}")
    return all_listings


def normalise_model(title: str) -> tuple[Optional[str], float]:
    """
    Use fuzzy string matching to map a listing title to a canonical model.

    Uses rapidfuzz's token_sort_ratio to handle word-order variations.

    Args:
        title: The listing title string

    Returns:
        Tuple of (canonical_model or None, match_score)
    """
    if not title:
        return None, 0.0

    match_result = process.extractOne(
        title,
        config.CANONICAL_MODELS,
        scorer=fuzz.token_sort_ratio
    )
    if match_result is None:
        return None, 0.0

    matched, score, _ = match_result
    if score >= config.FUZZY_MATCH_THRESHOLD:
        return matched, float(score)
    return None, float(score)


def is_miscategorised(canonical_model: Optional[str], category_full: str) -> bool:
    """
    Check if a listing's category matches the expected category for its model.

    Args:
        canonical_model: The fuzzy-matched canonical model name
        category_full: The listing's stated category

    Returns:
        True if the listing appears to be in the wrong category.
    """
    if not canonical_model:
        return False

    expected = config.MODEL_CATEGORY_MAP.get(canonical_model)
    if not expected:
        return False

    similarity = fuzz.token_set_ratio(category_full, expected)
    return similarity < config.FUZZY_CATEGORY_THRESHOLD


def store_listings(
    conn: sqlite3.Connection,
    listings: list[dict[str, Any]],
    query: str,
) -> None:
    """Store listings in the SQLite database, avoiding duplicates."""
    for listing in listings:
        try:
            price = listing.get("price", {})
            price_amount = float(price.get("amount", 0) or 0)
            price_currency = price.get("currency", "USD")

            condition = listing.get("condition", {})
            condition_name = condition.get("name", "") if isinstance(condition, dict) else str(condition)

            categories = listing.get("categories", [])
            category_full = categories[0].get("full_name", "") if categories else ""

            title = listing.get("title", "")
            canonical_model, fuzzy_score = normalise_model(title)

            conn.execute("""
                INSERT OR REPLACE INTO sold_listings
                (listing_id, title, make, model, price_amount, price_currency,
                 condition_name, category_full, year, url, fetched_at,
                 canonical_model, fuzzy_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                listing.get("id"),
                title,
                listing.get("make", ""),
                listing.get("model", ""),
                price_amount,
                price_currency,
                condition_name,
                category_full,
                listing.get("year", ""),
                listing.get("url", ""),
                datetime.now().isoformat(),
                canonical_model,
                fuzzy_score,
            ))
        except Exception as e:
            print(f"  Warning: Could not store listing {listing.get('id')}: {e}")

    conn.commit()


def load_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """Load all stored listings into a pandas DataFrame."""
    return pd.read_sql_query("SELECT * FROM sold_listings", conn)


def compute_price_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute median and std dev prices per (canonical_model, condition) group.
    Only groups with MIN_SOLD_COUNT or more listings are included.
    """
    df = df[df["canonical_model"].notna()].copy()
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby(["canonical_model", "condition_name"])["price_amount"].agg(
        median_price=("median"),
        std_price=("std"),
        count=("count"),
    ).reset_index()

    # Filter out groups with too few samples
    grouped = grouped[grouped["count"] >= config.MIN_SOLD_COUNT].copy()
    grouped["std_price"] = grouped["std_price"].fillna(0)
    return grouped


def flag_deals(
    df: pd.DataFrame,
    stats: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute z-scores and flag underpriced + miscategorised listings.

    Returns the DataFrame with added columns:
      - z_score
      - underpriced (bool)
      - miscategorised (bool)
      - deal_score (composite score for ranking)
    """
    df = df.merge(stats, on=["canonical_model", "condition_name"], how="left")

    # Compute z-score
    df["z_score"] = (
        (df["price_amount"] - df["median_price"]) / df["std_price"].replace(0, 1)
    )
    df.loc[df["std_price"] == 0, "z_score"] = 0  # No variance = no anomaly

    # Flag underpriced
    df["underpriced"] = df["z_score"] < config.Z_SCORE_THRESHOLD

    # Flag miscategorised
    df["miscategorised"] = df.apply(
        lambda row: is_miscategorised(row["canonical_model"], row["category_full"]),
        axis=1
    )

    # Composite deal score: lower z_score = bigger deal, miscategorised = bonus
    df["deal_score"] = -df["z_score"] + df["miscategorised"].astype(int)

    return df


def print_deal_summary(df: pd.DataFrame) -> None:
    """Print a summary of flagged deals to the console."""
    deals = df[df["underpriced"] | df["miscategorised"]].copy()

    if deals.empty:
        print("\nNo underpriced or miscategorised listings found.")
        return

    print(f"\n{'='*70}")
    print("FLAGGED DEALS")
    print(f"{'='*70}")
    print(f"Total flagged: {len(deals)}")
    print(f"  Underpriced: {deals['underpriced'].sum()}")
    print(f"  Miscategorised: {deals['miscategorised'].sum()}")
    print(f"{'='*70}\n")

    # Sort by deal score descending
    deals = deals.sort_values("deal_score", ascending=False)

    for _, row in deals.head(20).iterrows():
        flags = []
        if row["underpriced"]:
            flags.append("UNDERPRICED")
        if row["miscategorised"]:
            flags.append("MISCATEGORISED")
        print(f"[{','.join(flags)}] {row['title'][:50]}...")
        print(f"  Model: {row['canonical_model']} | Condition: {row['condition_name']}")
        print(f"  Price: GBP {row['price_amount']:.2f} | z-score: {row['z_score']:.2f}")
        print(f"  URL: {row['url']}")
        print()


def export_csv(df: pd.DataFrame, path: str) -> None:
    """Export the full dataset to CSV."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\nExported {len(df)} listings to {path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape and analyse Reverb sold listings for deals."
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Single search query (e.g. 'Gibson Les Paul')"
    )
    parser.add_argument(
        "--pages", "-p",
        type=int,
        default=config.API_MAX_PAGES,
        help="Max pages to fetch per query (default: 20)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all queries from config.SEARCH_QUERIES"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results to CSV after analysis"
    )
    args = parser.parse_args()

    if not args.query and not args.all:
        parser.print_help()
        print("\nUse --query 'MODEL NAME' or --all to run all configured queries.")
        sys.exit(1)

    # Setup database
    conn = setup_database(config.DB_PATH)

    # Determine queries to run
    queries = []
    if args.query:
        queries = [args.query]
    elif args.all:
        queries = config.SEARCH_QUERIES

    # Fetch and store
    total_fetched = 0
    for q in queries:
        listings = fetch_sold_listings(q, max_pages=args.pages)
        store_listings(conn, listings, q)
        total_fetched += len(listings)

    # Load and analyse
    df = load_data(conn)
    print(f"\nLoaded {len(df)} total listings from database.")

    stats = compute_price_stats(df)
    print(f"Computed price stats for {len(stats)} (model, condition) groups.")

    df = flag_deals(df, stats)
    print_deal_summary(df)

    if args.export:
        export_csv(df, config.CSV_OUTPUT_PATH)

    conn.close()


if __name__ == "__main__":
    main()
