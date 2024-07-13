from pathlib import Path

dashapp_rootdir = Path(__file__).resolve().parents[2]

awde_url = "https://www.abgeordnetenwatch.de/api/v2/"
cached_dataset = dashapp_rootdir / "data" / "votes_bundestag.parquet"
