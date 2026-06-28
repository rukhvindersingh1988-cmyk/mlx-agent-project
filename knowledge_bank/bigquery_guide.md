# The Comprehensive Guide to Google BigQuery

BigQuery is a fully managed, serverless enterprise data warehouse that enables scalable analysis over petabytes of data. This guide covers everything from standard SQL to advanced topics like BigQuery ML and Python integration.

---

## 1. Standard SQL Syntax

BigQuery uses Google Standard SQL, which is ANSI-compliant. 

### Basic Query
```sql
SELECT
  column_1,
  SUM(column_2) AS total
FROM
  `project.dataset.table`
WHERE
  date_column >= '2023-01-01'
GROUP BY
  column_1
ORDER BY
  total DESC
LIMIT 100;
```

### Common Table Expressions (CTEs)
CTEs improve readability and modularity.
```sql
WITH daily_sales AS (
  SELECT
    DATE(transaction_timestamp) AS sale_date,
    SUM(amount) AS daily_total
  FROM
    `my_project.sales.transactions`
  GROUP BY 1
)
SELECT * FROM daily_sales WHERE daily_total > 10000;
```

---

## 2. Partitioning and Clustering

To optimize performance and reduce costs, BigQuery supports partitioning (dividing a table into segments) and clustering (sorting data based on specific columns).

### Partitioning
You can partition by time-unit (date, timestamp, datetime) or integer range.
```sql
CREATE OR REPLACE TABLE `my_project.dataset.partitioned_table`
PARTITION BY DATE(transaction_timestamp)
AS
SELECT * FROM `my_project.dataset.raw_table`;
```

### Clustering
Clustering can be used with or without partitioning. It supports up to 4 columns.
```sql
CREATE OR REPLACE TABLE `my_project.dataset.clustered_table`
PARTITION BY DATE(transaction_timestamp)
CLUSTER BY customer_id, region
AS
SELECT * FROM `my_project.dataset.raw_table`;
```

---

## 3. JSON Extraction

BigQuery natively supports `JSON` data types and functions to parse and extract JSON data.

### Extracting Scalar Values
```sql
SELECT
  JSON_VALUE(json_column, '$.user.name') AS user_name,
  CAST(JSON_VALUE(json_column, '$.user.age') AS INT64) AS user_age
FROM
  `project.dataset.json_table`;
```

### Extracting JSON Arrays
```sql
SELECT
  JSON_QUERY_ARRAY(json_column, '$.items') AS items_array
FROM
  `project.dataset.json_table`;
```

---

## 4. Nested and Repeated Records (STRUCT / ARRAY)

BigQuery excels at handling denormalized data using `ARRAY` (repeated) and `STRUCT` (nested) types.

### Unnesting Arrays
To flatten an array, use the `UNNEST` function, typically with a `CROSS JOIN` (often implicit using a comma).
```sql
SELECT
  order_id,
  item.name,
  item.price
FROM
  `project.dataset.orders`,
  UNNEST(items) AS item;
```

### Working with Structs
```sql
SELECT
  user_id,
  address.city,
  address.zipcode
FROM
  `project.dataset.users`;
```

### Creating Arrays and Structs
```sql
SELECT
  1 AS id,
  ARRAY[1, 2, 3] AS numbers,
  STRUCT('John' AS first_name, 'Doe' AS last_name) AS name;
```

---

## 5. Window Functions

Window functions perform calculations across a set of table rows related to the current row, without grouping them into a single output row.

### ROW_NUMBER, RANK, and DENSE_RANK
```sql
SELECT
  department,
  employee,
  salary,
  ROW_NUMBER() OVER(PARTITION BY department ORDER BY salary DESC) as row_num,
  RANK() OVER(PARTITION BY department ORDER BY salary DESC) as rank,
  DENSE_RANK() OVER(PARTITION BY department ORDER BY salary DESC) as dense_rank
FROM
  `project.dataset.employees`;
```

### LAG and LEAD
```sql
SELECT
  date,
  daily_sales,
  LAG(daily_sales) OVER(ORDER BY date) as previous_day_sales,
  LEAD(daily_sales) OVER(ORDER BY date) as next_day_sales
FROM
  `project.dataset.sales_summary`;
```

---

## 6. BigQuery ML (BQML)

BigQuery ML enables users to create and execute machine learning models using standard SQL directly inside BigQuery.

### Training a Model
```sql
CREATE OR REPLACE MODEL `project.dataset.predict_churn`
OPTIONS(model_type='logistic_reg', input_label_cols=['churned']) AS
SELECT
  customer_id,
  tenure,
  monthly_charges,
  churned
FROM
  `project.dataset.customer_data`;
```

### Evaluating a Model
```sql
SELECT
  *
FROM
  ML.EVALUATE(MODEL `project.dataset.predict_churn`, (
    SELECT * FROM `project.dataset.customer_eval_data`
  ));
```

### Making Predictions
```sql
SELECT
  customer_id,
  predicted_churned
FROM
  ML.PREDICT(MODEL `project.dataset.predict_churn`, (
    SELECT * FROM `project.dataset.customer_new_data`
  ));
```

---

## 7. Python Client Integration

The `google-cloud-bigquery` library allows seamless interaction between Python and BigQuery. It integrates well with Pandas.

### Installation
```bash
pip install google-cloud-bigquery db-dtypes pandas
```

### Executing Queries and Loading into Pandas
```python
from google.cloud import bigquery
import pandas as pd

# Construct a BigQuery client object
client = bigquery.Client()

query = """
    SELECT name, SUM(number) as total_people
    FROM `bigquery-public-data.usa_names.usa_1910_2013`
    WHERE state = 'TX'
    GROUP BY name
    ORDER BY total_people DESC
    LIMIT 20
"""

# Execute the query
query_job = client.query(query)

# Wait for the job to complete and convert results to a Pandas DataFrame
df = query_job.to_dataframe()

print(df.head())
```

### Loading Data into BigQuery
```python
# Load DataFrame to a new BigQuery table
table_id = 'your-project.your_dataset.your_table_name'

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_TRUNCATE", # Options: WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY
)

job = client.load_table_from_dataframe(
    df, table_id, job_config=job_config
)

# Wait for the job to complete
job.result()
print(f"Loaded {job.output_rows} rows into {table_id}")
```
