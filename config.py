"""
Reverb Deals Finder - Configuration

Centralised configuration for the Reverb sold listings scraper.
"""

# === API Settings ===
REVERB_API_BASE = "https://api.reverb.com/api"
REVERB_API_HEADERS = {
    "Accept": "application/hal+json",
    "Accept-Version": "3.0",
}
API_DELAY_SECONDS = 0.5  # Delay between API calls to avoid rate limiting
API_MAX_PAGES = 20  # Max pages to fetch per search query
API_PER_PAGE = 50  # Items per page

# === Fuzzy Matching Settings ===
FUZZY_MATCH_THRESHOLD = 70  # Minimum score (0-100) to accept a model match
FUZZY_CATEGORY_THRESHOLD = 60  # Minimum score to accept a category match

# === Price Analysis Settings ===
Z_SCORE_THRESHOLD = -1.5  # Flag listings with price > 1.5 std devs below median
MIN_SOLD_COUNT = 3  # Minimum sold listings required to compute a reliable median

# === Data Storage ===
DATA_DIR = "data"
DB_PATH = "data/reverb_listings.db"
CSV_OUTPUT_PATH = "data/sold_listings.csv"

# === Search Queries ===
# Add your target models/brands here. The scraper will search for each.
SEARCH_QUERIES = [
    "Gibson Les Paul",
    "Fender Stratocaster",
    "Fender Telecaster",
    "Fender Jaguar",
    "Gibson ES-335",
    "Fender Jazz Bass",
    "Fender Precision Bass",
    "Gibson SG",
    "PRS Custom 24",
    "Rickenbacker",
    "Gretsch Electromatic",
    "Martin D-28",
    "Taylor 814",
]

# === Model Canonicalisation ===
# Maps fuzzy-matched titles to a canonical model name.
# These are the reference models used for grouping sold prices.
CANONICAL_MODELS = [
    "Gibson Les Paul Standard",
    "Gibson Les Paul Studio",
    "Gibson Les Paul Custom",
    "Fender Stratocaster",
    "Fender Telecaster",
    "Fender Jaguar",
    "Fender Jazzmaster",
    "Fender Jazz Bass",
    "Fender Precision Bass",
    "Gibson ES-335",
    "Gibson SG Standard",
    "PRS Custom 24",
    "Rickenbacker 4003",
    "Gretsch Electromatic",
    "Martin D-28",
    "Taylor 814",
]

# === Category Mappings ===
# Maps canonical models to their expected Reverb category for miscategorisation detection.
MODEL_CATEGORY_MAP = {
    "Gibson Les Paul Standard": "Electric Guitars",
    "Gibson Les Paul Studio": "Electric Guitars",
    "Gibson Les Paul Custom": "Electric Guitars",
    "Fender Stratocaster": "Electric Guitars",
    "Fender Telecaster": "Electric Guitars",
    "Fender Jaguar": "Electric Guitars",
    "Fender Jazzmaster": "Electric Guitars",
    "Fender Jazz Bass": "Bass Guitars",
    "Fender Precision Bass": "Bass Guitars",
    "Gibson ES-335": "Electric Guitars",
    "Gibson SG Standard": "Electric Guitars",
    "PRS Custom 24": "Electric Guitars",
    "Rickenbacker 4003": "Bass Guitars",
    "Gretsch Electromatic": "Electric Guitars",
    "Martin D-28": "Acoustic Guitars",
    "Taylor 814": "Acoustic Guitars",
}
