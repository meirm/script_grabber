# uv Single-File Script Examples

This directory contains example uv single-file scripts demonstrating various features and use cases.

## What are uv Scripts?

uv scripts are Python files that embed their dependency specifications using PEP 723 metadata blocks. This allows you to create self-contained, portable Python scripts that automatically manage their own dependencies.

## Format

```python
#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "package-name>=version",
#   "another-package",
# ]
# ///

import package_name
# Your code here
```

## Examples

### basic_deps.py
Demonstrates basic dependency management with commonly-used packages:
- `requests`: HTTP library
- `python-dotenv`: Environment variable management

**Usage:**
```bash
# Copy to queue
cp basic_deps.py /path/to/cluster/queue/

# Or run directly with uv
uv run basic_deps.py
```

### data_analysis.py
Shows how to use data science libraries in a uv script:
- `pandas`: Data manipulation and analysis
- `numpy`: Numerical computing

**Usage:**
```bash
cp data_analysis.py /path/to/cluster/queue/
```

### version_constraints.py
Demonstrates various dependency version constraint formats:
- `>=`, `<`: Minimum and maximum versions
- `~=`: Compatible release (patch-level changes only)

**Usage:**
```bash
cp version_constraints.py /path/to/cluster/queue/
```

## Running Examples

### Via ScriptGrabber

1. Start a grabber:
```bash
grabber worker1 /path/to/cluster --job-timeout 300
```

2. Copy a script to the queue:
```bash
cp examples/uv_scripts/basic_deps.py /path/to/cluster/queue/
```

3. Check the logs:
```bash
# Script output
cat /path/to/cluster/log/basic_deps.py.out

# Dependency installation log
cat /path/to/cluster/log/basic_deps.py_uv_install.log

# Job status
ls /path/to/cluster/spool/worker1/*basic_deps.py*
```

### Directly with uv

You can also run these scripts directly using uv (without ScriptGrabber):

```bash
cd examples/uv_scripts
uv run basic_deps.py
```

## Creating Your Own uv Scripts

1. Start with the shebang:
```python
#!/usr/bin/env -S uv run
```

2. Add the PEP 723 metadata block:
```python
# /// script
# dependencies = [
#   "your-package>=1.0.0",
# ]
# ///
```

3. Write your Python code:
```python
import your_package

# Your code here
```

4. Make it executable:
```bash
chmod +x your_script.py
```

## Version Constraint Syntax

uv supports standard Python version specifiers:

- `package`: Latest version
- `package==1.2.3`: Exact version
- `package>=1.2.3`: Minimum version
- `package<2.0.0`: Maximum version (exclusive)
- `package>=1.2,<2.0`: Range
- `package~=1.2`: Compatible release (1.2.x)
- `package[extra]`: Package with extras

## Troubleshooting

### "uv not found" error
Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Dependency installation fails
Check the installation log:
```bash
cat /path/to/cluster/log/your_script.py_uv_install.log
```

Common issues:
- Package name typo
- Version not available
- Network connectivity

### Script fails to execute
Check the error log:
```bash
cat /path/to/cluster/log/your_script.py.err
```

## Additional Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [PEP 723 Specification](https://peps.python.org/pep-0723/)
- [ScriptGrabber Documentation](../../README.md)
