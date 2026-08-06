import argparse
import os
from datetime import datetime
from typing import Optional

import pandas as pd
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery


DOMAIN_FILTERS = {
    "medical-devices": "EXISTS(SELECT 1 FROM UNNEST(cpc) AS c WHERE c.code LIKE 'A61%' OR c.code LIKE 'A61B%' OR c.code LIKE 'A61C%' OR c.code LIKE 'A61F%' OR c.code LIKE 'A61H%' OR c.code LIKE 'A61K%' OR c.code LIKE 'A61L%' OR c.code LIKE 'A61M%' OR c.code LIKE 'A61N%' OR c.code LIKE 'A61P%' OR c.code LIKE 'A61Q%' OR c.code LIKE 'A61R%')",
    "consumer-electronics": "EXISTS(SELECT 1 FROM UNNEST(cpc) AS c WHERE c.code LIKE 'H04R%' OR c.code LIKE 'H04L%' OR c.code LIKE 'H04W%' OR c.code LIKE 'H04M%' OR c.code LIKE 'H04N%' OR c.code LIKE 'G06F%' OR c.code LIKE 'G10L%' OR c.code LIKE 'H05B%')",
}

def validate_date(date_text: str) -> str:
    try:
        datetime.strptime(date_text, "%Y%m%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Date must be in YYYYMMDD format") from exc
    return date_text


def build_query(
    limit: int,
    country_code: Optional[str] = None,
    cpc_class: Optional[str] = None,
    domain: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    where_clauses = []
    if country_code:
        where_clauses.append(f"country_code = '{country_code}'")
    if cpc_class:
        where_clauses.append(f"EXISTS(SELECT 1 FROM UNNEST(cpc) AS c WHERE c.code LIKE '{cpc_class}%')")
    if domain:
        filter_expr = DOMAIN_FILTERS.get(domain)
        if not filter_expr:
            raise ValueError(f"Unknown domain: {domain}. Supported values: {', '.join(DOMAIN_FILTERS.keys())}")
        where_clauses.append(filter_expr)
    if start_date:
        where_clauses.append(f"publication_date >= {int(start_date)}")
    if end_date:
        where_clauses.append(f"publication_date <= {int(end_date)}")

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


def build_search_text(row: pd.Series) -> str:
    title = str(row.get("title", "")).strip()
    abstract = str(row.get("abstract", "")).strip()
    claims = str(row.get("claims", "")).strip()

    parts = [title, abstract]
    if claims:
        claims_preview = " ".join(claims.split())[:1800]
        parts.append(claims_preview)

    return " ".join(part for part in parts if part)


def prepare_output_df(df: pd.DataFrame) -> pd.DataFrame:
    output_df = df[["publication_number", "title", "abstract", "publication_date", "country_code", "cpc"]].copy()
    output_df["search_text"] = df.apply(build_search_text, axis=1)
    output_df["claims_preview"] = df["claims"].apply(lambda value: " ".join(str(value).split())[:1200] if value else "")
    return output_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a sample of patents from Google Patents Public Data")
    parser.add_argument("--project-id", required=True, help="Google Cloud project ID for BigQuery")
    parser.add_argument("--limit", type=int, default=50000, help="Number of patents to download (default: 50000)")
    parser.add_argument("--output", default="patents_50k.csv", help="Output CSV file path")
    parser.add_argument("--country-code", default=None, help="Optional country code filter, e.g. US")
    parser.add_argument("--cpc-class", default=None, help="Optional CPC class prefix filter, e.g. G06")
    parser.add_argument(
        "--domain",
        default=None,
        choices=list(DOMAIN_FILTERS.keys()),
        help="Optional preset domain filter. Supported values: medical-devices, consumer-electronics.",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        type=validate_date,
        help="Optional start publication date filter in YYYYMMDD format.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        type=validate_date,
        help="Optional end publication date filter in YYYYMMDD format.",
    )
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

    query = build_query(args.limit, args.country_code, args.cpc_class, args.domain, args.start_date, args.end_date)

    print(f"Running query for up to {args.limit} patents...")
    df = client.query(query).to_dataframe()

    df = df.fillna("")
    output_df = prepare_output_df(df)
    output_df.to_csv(args.output, index=False)

    print(f"Saved {len(output_df)} patents to {os.path.abspath(args.output)}")
    print("Columns:", ", ".join(output_df.columns))


if __name__ == "__main__":
    main()
