#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "pandas>=1.5.0",
#     "numpy<2.0.0",
#     "requests==2.31.0"
# ]
# ///
import pandas as pd
import numpy as np
import requests

print(f"Pandas version: {pd.__version__}")
print(f"NumPy version: {np.__version__}")
print(f"Requests version: {requests.__version__}")