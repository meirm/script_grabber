#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The `script_grabber` package provides a distributed job scheduling system based on a master-grabber architecture.

This package consists of two main scripts:
- `grabmaster.py`: A Python script that manages the job queue and schedules job execution by grabbers.
- `grabber.py`: A Python script that fetches jobs from the queue and executes them.

Both scripts rely on a shared file system for communication and coordination between grabbers.

This package also includes a `Dockerfile` and `docker-compose.yaml` to run the grabmaster and one grabber in a Docker container.

Author: Meir Michanie
Email: meirm@riunx.com
License: MIT
"""

# Import standard library modules here.

# Import third-party modules here.

# Import local modules here.

# Define exceptions here
class GrabError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class GrabTimeoutError(GrabError):
    pass

class GrabConnectionError(GrabError):
    pass

class GrabNetworkError(GrabError):
    pass

class GrabMisuseError(GrabError):
    pass

class GrabConfigError(GrabError):
    pass

class GrabLockError(GrabError):
    pass

class GrabRerunError(GrabError):
    """Raised when a rerun operation fails."""
    pass

class GrabTaskNotFoundError(GrabRerunError):
    """Raised when a task to rerun cannot be found in the spool directory."""
    pass