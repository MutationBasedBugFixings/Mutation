import pandas as pd
import numpy as np

def calculate_dataset_stats(csv_path, confidence_z=1.96):
    """
    Calculates the Proportion, Standard Error, and Confidence Intervals 
    for each Mutant Operator in the dataset.
    
    Args:
        csv_path: Path to the CSV file.
        confidence_z: Z-score (1.96 for 95%, 2.576 for 99% as per your link).
    """
    df = pd.read_csv(csv_path)
    
    # Standardize column names (handling trailing spaces and typos)
    df.columns = [col.strip() for col in df.columns]
    col = 'Munatnt Operator'
    
    # Filter out non-mutant entries ('no')
    mutants = df[df[col].astype(str).str.lower() != 'no'].copy()
    
    # Total count of valid mutated samples (N)
    N = len(mutants)
    
    # Calculate counts and proportions
    counts = mutants[col].value_counts()
    
    results = []
    for operator, count in counts.items():
        p = count / N  # Observed proportion
        
        # Formula for Margin of Error (MOE): Z * sqrt( p*(1-p) / N )
        # This matches the logic of the sample size calculator provided
        se = np.sqrt((p * (1 - p)) / N)
        moe = confidence_z * se
        
        results.append({
            'Operator': str(operator).strip(),
            'Count': count,
            'Proportion': f"{p:.2%}",
            'Margin of Error': f"{moe:.2%}",
            '95% CI Lower': f"{max(0, p - moe):.2%}",
            '95% CI Upper': f"{min(1, p + moe):.2%}"
        })
    
    return pd.DataFrame(results), N

# Example Execution
bip_stats, bip_n = calculate_dataset_stats('BugInPy.xlsx - Sheet1.csv')
d4j_stats, d4j_n = calculate_dataset_stats('Defects4j.csv')

print(f"BugInPy (N={bip_n}) Statistical Summary:\n", bip_stats.head())
print(f"\nDefects4j (N={d4j_n}) Statistical Summary:\n", d4j_stats.head())

# To save the results:
# bip_stats.to_csv('BugInPy_Statistical_Analysis.csv', index=False)
