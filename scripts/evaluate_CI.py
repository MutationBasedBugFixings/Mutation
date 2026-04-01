import pandas as pd
import numpy as np
import math

def calculate_sampling_and_ci(file_path, N, n, seed=20260322):
    """
    Performs random sampling and calculates 95% CI with Finite Population Correction.
    """
    # 1. Load the dataset
    df = pd.read_csv(file_path)
    
    # Clean column names (handle trailing spaces/typos like 'Munatnt')
    df.columns = [col.strip() for col in df.columns]
    op_col = 'Munatnt Operator'
    
    # 2. Generate random numbers for sampling (Step 3 & 4 of methodology)
    np.random.seed(seed)
    df['Random_Number'] = np.random.rand(len(df))
    df_sorted = df.sort_values(by='Random_Number')
    
    # 3. Select the first n rows as the random sample (Step 5)
    sample = df_sorted.head(n).copy()
    
    # 4. Infer Repairable status (Step 6)
    # Yes if operator is not blank and not 'no'
    def infer_repairable(val):
        val = str(val).strip().lower()
        if val == 'nan' or val == '' or val == 'no':
            return 'No'
        return 'Yes'
    
    sample['Repairable_inferred'] = sample[op_col].apply(infer_repairable)
    
    # 5. Statistical Calculations (Step 7)
    x = len(sample[sample['Repairable_inferred'] == 'Yes'])
    p = x / n
    
    # Standard error for proportion
    standard_error = math.sqrt((p * (1 - p)) / n)
    
    # Finite Population Correction (FPC) factor
    fpc = math.sqrt((N - n) / (N - 1))
    
    # Margin of Error for 95% Confidence (Z = 1.96)
    margin_of_error = 1.96 * standard_error * fpc
    
    lower_bound = p - margin_of_error
    upper_bound = p + margin_of_error
    
    return {
        'Population_N': N,
        'Sample_n': n,
        'Repairable_Count_x': x,
        'Proportion_p': p,
        'Margin_of_Error': margin_of_error,
        'CI_Lower': lower_bound,
        'CI_Upper': upper_bound,
        'Sampled_Data': sample
    }

# --- Execution for your datasets ---

# Parameters from your Summary.csv
# Python: N=300, n=169
# Java: N=803, n=260

python_results = calculate_sampling_and_ci('BugInPy.xlsx - Sheet1.csv', N=300, n=169)
java_results = calculate_sampling_and_ci('Defects4j.csv', N=803, n=260)

# Display Results
for name, res in [("Python (BugInPy)", python_results), ("Java (Defects4j)", java_results)]:
    print(f"--- Results for {name} ---")
    print(f"Sample Proportion (p): {res['Proportion_p']:.4f}")
    print(f"Margin of Error (95%): {res['Margin_of_Error']:.4f}")
    print(f"95% CI: [{res['CI_Lower']:.4f}, {res['CI_Upper']:.4f}]")
    print("-" * 30)

# Save the sampled data to match your 'sampled.csv' files
# python_results['Sampled_Data'].to_csv('Python_sampled_generated.csv', index=False)
# java_results['Sampled_Data'].to_csv('Java_sampled_generated.csv', index=False)
