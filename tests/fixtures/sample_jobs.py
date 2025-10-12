"""Sample job scripts for testing."""

SUCCESS_JOB = '''#!/usr/bin/env python3
"""A simple job that succeeds."""
import sys
print("Job started successfully")
print("Processing data...")
sys.stderr.write("No errors\\n")
print("Job completed")
sys.exit(0)
'''

FAILURE_JOB = '''#!/usr/bin/env python3
"""A job that fails with non-zero exit code."""
import sys
print("Job started")
sys.stderr.write("ERROR: Something went wrong\\n")
print("Failed to process data")
sys.exit(1)
'''

TIMEOUT_JOB = '''#!/usr/bin/env python3
"""A job that simulates timeout (exit code 124)."""
import sys
print("Job started but will timeout")
sys.stderr.write("TIMEOUT: Operation took too long\\n")
sys.exit(124)
'''

LONG_RUNNING_JOB = '''#!/usr/bin/env python3
"""A job that runs for a specified duration."""
import sys
import time
duration = int(sys.argv[1]) if len(sys.argv) > 1 else 5
print(f"Running for {duration} seconds...")
time.sleep(duration)
print("Job completed after sleep")
sys.exit(0)
'''

OUTPUT_JOB = '''#!/usr/bin/env python3
"""A job that writes to both stdout and stderr."""
import sys
print("Line 1 to stdout")
sys.stderr.write("Line 1 to stderr\\n")
print("Line 2 to stdout")
sys.stderr.write("Line 2 to stderr\\n")
print("Line 3 to stdout")
sys.exit(0)
'''

ENV_JOB = '''#!/usr/bin/env python3
"""A job that uses environment variables."""
import os
import sys
test_var = os.environ.get('TEST_VAR', 'default_value')
print(f"TEST_VAR = {test_var}")
sys.exit(0)
'''

EXCEPTION_JOB = '''#!/usr/bin/env python3
"""A job that raises an exception."""
import sys
print("Job started")
raise RuntimeError("Intentional exception for testing")
sys.exit(1)
'''
