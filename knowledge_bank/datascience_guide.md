# Data Science & Analysis Guide

## CRITICAL RULE FOR AI AGENT:
When asked to analyse data, plot charts, or process CSV/JSON files, use your `run_command`
and `write_file` tools to do the work. Show results. Do NOT just give the user instructions.

## Key Libraries
```bash
pip install pandas numpy matplotlib seaborn scipy scikit-learn plotly
```

## Pandas Quick Reference
```python
import pandas as pd

# Read data
df = pd.read_csv("data.csv")
df = pd.read_json("data.json")
df = pd.read_excel("data.xlsx")

# Inspect
df.head()           # First 5 rows
df.info()           # Column types and nulls
df.describe()       # Statistical summary
df.shape            # (rows, columns)
df.columns.tolist() # Column names

# Filter
df[df["age"] > 30]                  # Row filter
df[df["city"].isin(["NY", "LA"])]   # Multiple values
df.dropna()                          # Drop null rows
df.fillna(0)                         # Fill nulls

# Aggregate
df.groupby("category")["value"].sum()
df["column"].value_counts()
df.pivot_table(values="sales", index="region", columns="year", aggfunc="sum")

# Save
df.to_csv("output.csv", index=False)
df.to_json("output.json", orient="records")
```

## Matplotlib Quick Charts
```python
import matplotlib.pyplot as plt

# Line chart
plt.plot(x, y)
plt.title("My Chart")
plt.savefig("chart.png")
plt.show()

# Bar chart
plt.bar(categories, values)

# Histogram
plt.hist(data, bins=20)

# Scatter plot
plt.scatter(x, y)
```

## scikit-learn Quick Model
```python
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = LinearRegression()
model.fit(X_train, y_train)
predictions = model.predict(X_test)
print(f"MSE: {mean_squared_error(y_test, predictions):.4f}")
```
