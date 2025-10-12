#!/usr/bin/env python3
"""
Sample job: Failing Job

This job intentionally fails to demonstrate error handling.
"""

import sys

print("Starting job...")
print("About to fail...")

sys.stderr.write("ERROR: This job is designed to fail for testing purposes\n")
sys.exit(1)
