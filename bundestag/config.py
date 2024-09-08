from pathlib import Path

dashapp_rootdir = Path(__file__).resolve().parents[1]
# we use en/de, DeepL uses EN-GB/DE
language = "de"
language_codes = {
    "de": "DE",
    "en": "EN-GB",
}

awde_url = "https://www.abgeordnetenwatch.de/api/v2/"
cached_dataset = dashapp_rootdir / "data" / "votes_bundestag.parquet"
