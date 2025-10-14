#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "certifi>=2020.0.0,<2026.0.0",
#   "python-dateutil~=2.8",
# ]
# ///

"""
Version Constraints Example

Demonstrates various dependency version constraint formats:
- >= and <: Minimum and maximum versions
- ~=: Compatible release (allows patch-level changes)
"""

import certifi
from dateutil import parser
from datetime import datetime

def main():
    print("=== Version Constraints uv Script Demo ===")
    print(f"Certifi version: {certifi.__version__}")

    # Use python-dateutil to parse dates
    date_string = "2024-10-14 15:30:00"
    parsed_date = parser.parse(date_string)

    print(f"\nParsed date: {parsed_date}")
    print(f"Current time: {datetime.now()}")

    print("\n✅ Script with version constraints completed successfully!")
    return 0

if __name__ == "__main__":
    exit(main())
