# BigQuery Knowledge Sheet

Google BigQuery can be queried directly from the terminal or using python client libraries.

## Python Integration
Use `google-cloud-bigquery` library.
```python
from google.cloud import bigquery

def run_query(query_str):
    client = bigquery.Client()
    query_job = client.query(query_str)
    results = query_job.result()
    return [dict(row) for row in results]
```

## CLI Commands
Use the `bq` command-line tool (part of the Google Cloud SDK).

* **Run a query:**
  ```bash
  bq query --use_legacy_sql=false "SELECT count(*) FROM \`project.dataset.table\`"
  ```
* **List datasets in a project:**
  ```bash
  bq ls --project_id your_project_id
  ```
* **List tables in a dataset:**
  ```bash
  bq ls your_project_id:your_dataset
  ```
* **Show table schema:**
  ```bash
  bq show your_project_id:your_dataset.your_table
  ```

## Authentication
Authentication is managed via Application Default Credentials (ADC):
```bash
gcloud auth application-default login
```
Or via service account key file path set in the environment:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```
