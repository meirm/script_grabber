#!/usr/bin/env python3
"""
Sample job: Hello World

This is a simple example job that demonstrates basic output.
Upload this file through the web interface to test the system.
"""

import sys
from datetime import datetime

print("Hello from ScriptGrabber!")
print(f"Job started at: {datetime.now()}")
print("This is a test job running in the distributed cluster.")

# Write to stderr as well
sys.stderr.write("This is an info message to stderr\n")

print("\nJob completed successfully!")
sys.exit(0)
