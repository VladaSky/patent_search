import argparse
import os
from typing import Optional

import pandas as pd
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery


def build_query(limit: int, country_code: Optional[str] = None, cpc_class: Optional[str] = None) -> str:
    where_clauses = []
    if country_code:
        where_clauses.append(f"country_code = '{country_code}'")
    if cpc_class:
        where_clauses.append(f"REGEXP_CONTAINS(TO_JSON_STRING(cpc), r'{cpc_class}')")

    where_sql = "\nAND ".join(where_clauses)
    if where_sql:
        where_sql = f"WHERE {where_sql}"

    return f"""
    SELECT
        publication_number,
        COALESCE((SELECT t.text FROM UNNEST(title_localized) AS t WHERE t.language = 'en' LIMIT 1), '') AS title,
        COALESCE((SELECT t.text FROM UNNEST(abstract_localized) AS t WHERE t.language = 'en' LIMIT 1), '') AS abstract,
        COALESCE((SELECT t.text FROM UNNEST(claims_localized) AS t WHERE t.language = 'en' LIMIT 1), '') AS claims,
        publication_date,
        country_code,
        cpc
    FROM `patents-public-data.patents.publications`
    {where_sql}
    ORDER BY publication_date DESC
    LIMIT {limit}
    """


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a sample of patents from Google Patents Public Data")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID for BigQuery")
    parser.add_argument("--limit", type=int, default=50000, help="Number of patents to download (default: 50000)")
    parser.add_argument("--output", default="patents_50k.csv", help="Output CSV file path")
    parser.add_argument("--country-code", default=None, help="Optional country code filter, e.g. US")
    parser.add_argument("--cpc-class", default=None, help="Optional CPC class prefix filter, e.g. G06")
    parser.add_argument(
        "--credentials-file",
        default=None,
        help="Optional path to a Google service-account JSON key. If omitted, Application Default Credentials are used.",
    )
    args = parser.parse_args()

    if args.limit <= 0:
        raise ValueError("--limit must be greater than 0")

    try:
        if args.credentials_file:
            client = bigquery.Client.from_service_account_json(args.credentials_file, project=args.project_id)
        else:
            client = bigquery.Client(project=args.project_id)
    except DefaultCredentialsError as exc:
        raise SystemExit(
            "Google authentication failed. Set up credentials by either:\n"
            "1) running 'gcloud auth application-default login' (if the Google Cloud CLI is installed), or\n"
            "2) setting GOOGLE_APPLICATION_CREDENTIALS to a service account JSON key file, or\n"
            "3) passing --credentials-file /path/to/service-account.json"
        ) from exc

    query = build_query(args.limit, args.country_code, args.cpc_class)

    print(f"Running query for up to {args.limit} patents...")
    df = client.query(query).to_dataframe()

    df = df.fillna("")
    df.to_csv(args.output, index=False)

    print(f"Saved {len(df)} patents to {os.path.abspath(args.output)}")
    print("Columns:", ", ".join(df.columns))


if __name__ == "__main__":
    main()
