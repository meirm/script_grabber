#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests>=2.31.0",
#   "python-dotenv>=1.0.0",
# ]
# ///

"""
Basic uv Script Example

This script demonstrates a simple uv single-file script with two dependencies:
- requests: For making HTTP requests
- python-dotenv: For loading environment variables

The script fetches data from a public API and displays the result.
"""

import requests
from dotenv import load_dotenv

def main():
    print("=== Basic uv Script Demo ===")
    print(f"Requests version: {requests.__version__}")

    # Make a simple HTTP request
    try:
        response = requests.get("https://httpbin.org/json")
        response.raise_for_status()

        print(f"\nHTTP Status: {response.status_code}")
        print(f"Response Data: {response.json()}")

        print("\n✅ Script completed successfully!")
        return 0

    except requests.RequestException as e:
        print(f"\n❌ Error making request: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
