# Patent Semantic Search

This project builds a semantic patent search system that lets a user describe an idea in natural language and retrieve the most similar existing patents.

## Goal

The long-term goal is to help determine whether an invention is likely already covered by prior art before filing a new patent.

## Current status

- A local Python environment is set up in `.venv`
- A downloader script is included to pull patent records from Google Patents Public Data
- A small test dataset has been downloaded as `patents_test.csv`

## Project structure

- `download_patents.py` – downloads a sample of patents from Google Patents Public Data
- `requirements.txt` – Python dependencies for the downloader
- `patents_test.csv` – a small sample of downloaded patents for testing

## Setup

1. Create and activate the virtual environment:

   ```bash
   cd "/Users/vladabalinsky/Desktop/Grad School Stuff/patent_prior_art_search"
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the downloader:

   ```bash
   python download_patents.py --project-id YOUR_PROJECT_ID --limit 50000 --output patents_50k.csv
   ```

### Field-specific downloads

To pull a more focused sample, use the `--domain` option.

Medical devices:

```bash
python download_patents.py --project-id YOUR_PROJECT_ID --domain medical-devices --limit 50000 --output patents_medical_devices.csv
```

Consumer electronics:

```bash
python download_patents.py --project-id YOUR_PROJECT_ID --domain consumer-electronics --limit 50000 --output patents_consumer_electronics.csv
```

### Narrow by publication date to reduce query cost

If your project hits BigQuery free-query limits, adding a date range can reduce scanned bytes significantly:

```bash
python download_patents.py --project-id YOUR_PROJECT_ID --domain medical-devices --start-date 20240101 --end-date 20240630 --limit 50000 --output patents_medical_devices_recent.csv
```

If you need older patents, widen the date range gradually.

## Notes

The downloader uses Google BigQuery access to the public patent dataset. Authentication is required through Google Cloud credentials.

## Next steps

- build embeddings for patent titles/abstracts/claims
- create a vector index for similarity search
- add a simple search interface or API
