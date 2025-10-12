#!/usr/bin/env python3
"""
Sample job: Data Processing Example

This demonstrates a more realistic job that processes data.
"""

import sys
import time
from datetime import datetime

def process_data():
    """Simulate data processing."""
    print(f"Starting data processing at {datetime.now()}")

    # Simulate some work
    data = list(range(100))

    print(f"Processing {len(data)} items...")
    for i, item in enumerate(data):
        if i % 20 == 0:
            print(f"Progress: {i}/{len(data)}")
        time.sleep(0.01)  # Simulate work

    print(f"Processing complete at {datetime.now()}")
    return len(data)

if __name__ == "__main__":
    try:
        result = process_data()
        print(f"\nSuccessfully processed {result} items")
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"ERROR: {str(e)}\n")
        sys.exit(1)
