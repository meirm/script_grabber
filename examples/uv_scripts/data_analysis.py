#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "pandas>=2.0.0",
#   "numpy>=1.24.0",
# ]
# ///

"""
Data Analysis Example

Demonstrates using data science libraries in a uv script.
Creates a simple dataset, performs analysis, and displays results.
"""

import pandas as pd
import numpy as np

def main():
    print("=== Data Analysis uv Script Demo ===")
    print(f"Pandas version: {pd.__version__}")
    print(f"NumPy version: {np.__version__}")

    # Create sample data
    data = {
        'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
        'age': [25, 30, 35, 28, 32],
        'score': [92, 88, 95, 85, 90]
    }

    df = pd.DataFrame(data)

    print("\n📊 Dataset:")
    print(df)

    print("\n📈 Statistics:")
    print(df.describe())

    print("\n🎯 Analysis:")
    print(f"Average age: {df['age'].mean():.1f}")
    print(f"Average score: {df['score'].mean():.1f}")
    print(f"Highest score: {df['score'].max()} ({df.loc[df['score'].idxmax(), 'name']})")

    print("\n✅ Analysis completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
