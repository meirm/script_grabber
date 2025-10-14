"""
Test fixtures for uv single-file scripts.

Contains sample uv scripts for testing various scenarios:
- Valid uv scripts with dependencies
- Scripts with version constraints
- Scripts with optional dependencies
- Invalid metadata formats
- Edge cases
"""

# Basic uv script with simple dependencies
BASIC_UV_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests",
#   "python-dotenv",
# ]
# ///

import requests
import dotenv

print(f"Requests version: {requests.__version__}")
print("Basic uv script executed successfully")
'''

# Script with version constraints
VERSION_CONSTRAINTS_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests>=2.31.0",
#   "python-dotenv>=1.0.0,<2.0.0",
# ]
# ///

import requests
print(f"Requests version: {requests.__version__}")
print("Version constraints script executed successfully")
'''

# Script with optional dependencies
OPTIONAL_DEPS_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests",
# ]
# [optional-dependencies]
# dev = ["pytest", "black"]
# ///

import requests
print("Optional dependencies script executed successfully")
'''

# Script with alternative shebang format
ALT_SHEBANG_SCRIPT = '''#!/usr/bin/env uv run
# /// script
# dependencies = ["requests"]
# ///

import requests
print("Alternative shebang script executed successfully")
'''

# Script with invalid TOML (unclosed bracket)
INVALID_TOML_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests",
# ///

print("This should not execute")
'''

# Script with missing end marker
MISSING_END_MARKER_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = ["requests"]

print("This should not execute")
'''

# Script with no metadata block
NO_METADATA_SCRIPT = '''#!/usr/bin/env -S uv run

import sys
print("Script without metadata")
'''

# Regular Python script (not uv)
REGULAR_PYTHON_SCRIPT = '''#!/usr/bin/env python3

print("Regular Python script")
'''

# Bash script (not uv)
BASH_SCRIPT = '''#!/bin/bash

echo "Bash script"
'''

# Script with empty dependencies list
EMPTY_DEPS_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///

print("Script with no dependencies executed successfully")
'''

# Script that uses the dependencies
SCRIPT_WITH_USAGE = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests",
# ]
# ///

import requests
import sys

response = requests.get("https://httpbin.org/json")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
sys.exit(0)
'''

# Script that fails (exits with non-zero)
FAILING_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = ["requests"]
# ///

import sys
print("This script will fail")
sys.exit(1)
'''

# Script that times out
TIMEOUT_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = []
# ///

import time
print("Starting long operation...")
time.sleep(300)  # 5 minutes
print("Finished")
'''

# Script with invalid package name
INVALID_PACKAGE_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "this-package-does-not-exist-12345",
# ]
# ///

print("This should not execute")
'''

# Script with multiple dependency formats
COMPLEX_DEPS_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "requests>=2.31.0",
#   "python-dotenv~=1.0",
#   "certifi",
# ]
# ///

import requests
import dotenv
import certifi

print("Complex dependencies script executed successfully")
print(f"Requests: {requests.__version__}")
print(f"Certifi: {certifi.__version__}")
'''

# Script with package extras
PACKAGE_EXTRAS_SCRIPT = '''#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "httpx[http2]",
# ]
# ///

import httpx
print(f"httpx version: {httpx.__version__}")
print("Package extras script executed successfully")
'''
