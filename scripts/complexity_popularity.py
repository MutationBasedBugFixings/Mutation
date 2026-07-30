import pandas as pd
from scipy.stats import spearmanr, kendalltau

# Data from Table VIII
data = [
    ("MCR", "High", 32.1),
    ("CI", "Extremely High", 26.0),
    ("MRV", "Moderate", 17.6),
    ("LOR", "Low", 10.3),
    ("VA", "Extremely High", 7.1),
    ("MOCS", "Extremely High", 7.1),
    ("SI", "Moderate", 5.2),
    ("MPM", "High", 5.0),
    ("ROR", "Low", 4.9),
    ("SD", "Low", 3.2),
    ("DOC", "Low", 2.8),
    ("CR", "High", 2.7),
    ("MA", "High", 2.6),
    ("AIS", "Low", 2.3),
    ("SR", "Moderate", 2.2),
    ("DTR", "Moderate", 2.0),
    ("VR", "Moderate", 2.0),
    ("EII", "Moderate", 1.8),
    ("CFSM", "Moderate", 1.4),
    ("BCO", "Moderate", 1.3),
    ("EI", "Moderate", 1.3),
    ("FLI", "Moderate", 1.2),
    ("SM", "Low", 1.2),
    ("CASEI", "Moderate", 1.0),
    ("WLI", "Moderate", 0.9),
    ("AA", "Low", 0.8),
    ("AOR", "Low", 0.7),
    ("ElseI", "Low", 0.5),
    ("BWO", "Low", 0.5),
    ("RAR", "Low", 0.4),
    ("BR", "Low", 0.3),
    ("DIS", "Low", 0.3),
    ("CN", "Low", 0.3),
]

df = pd.DataFrame(
    data,
    columns=["Operator", "Complexity_Label", "Popularity_Percent"]
)

# Convert ordinal complexity labels to numeric values
complexity_mapping = {
    "Low": 1,
    "Moderate": 2,
    "High": 3,
    "Extremely High": 4
}

df["Complexity_Score"] = df["Complexity_Label"].map(
    complexity_mapping
)

# Spearman rank correlation
rho, spearman_p = spearmanr(
    df["Complexity_Score"],
    df["Popularity_Percent"]
)

# Optional robustness check
tau, kendall_p = kendalltau(
    df["Complexity_Score"],
    df["Popularity_Percent"],
    variant="b"
)

print(f"Number of operators: {len(df)}")
print(f"Spearman rho: {rho:.4f}")
print(f"Spearman p-value: {spearman_p:.6f}")
print(f"Kendall tau-b: {tau:.4f}")
print(f"Kendall p-value: {kendall_p:.6f}")

# Save the analyzed dataset
df.to_csv(
    "complexity_popularity_correlation.csv",
    index=False
)
