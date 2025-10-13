#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI module for rerunning completed tasks in the ScriptGrabber system.

This module provides a command-line interface for rerunning jobs that have
completed execution (DONE, FAILED, or TIMEOUT states).

Author: Meir Michanie
Email: meirm@riunx.com
License: MIT
"""

import argparse
import logging
import sys
from pathlib import Path

from .grabber import Grabber
from .grabexceptions import GrabTaskNotFoundError, GrabRerunError


def main():
    """
    Main entry point for the grabber-rerun CLI command.

    Parses command-line arguments and executes the task rerun operation.
    """
    parser = argparse.ArgumentParser(
        description="Rerun a completed task in the ScriptGrabber cluster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rerun a job to the common queue
  grabber-rerun worker1 /shared/cluster test_job.py

  # Rerun a job to a specific grabber's control queue
  grabber-rerun worker1 /shared/cluster test_job.py --queue-type control
        """
    )

    parser.add_argument(
        "grabber_name",
        help="Name of the grabber instance that executed the job"
    )

    parser.add_argument(
        "cluster_path",
        help="Path to the cluster directory"
    )

    parser.add_argument(
        "job_name",
        help="Name of the job to rerun (e.g., test_job.py)"
    )

    parser.add_argument(
        "--queue-type",
        choices=["common", "control"],
        default="common",
        help="Target queue type (default: common)"
    )

    args = parser.parse_args()

    # Configure logging
    log_dir = Path(args.cluster_path) / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "rerun.log"

    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="[%(asctime)s][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger = logging.getLogger("rerun")

    try:
        # Create Grabber instance (without calling run())
        grabber = Grabber(
            name=args.grabber_name,
            clusterpath=args.cluster_path
        )

        # Perform the rerun operation
        target_path = grabber.rerun_task(
            job_name=args.job_name,
            target_queue=args.queue_type
        )

        # Success message
        print(f"✓ Successfully requeued job: {args.job_name}")
        print(f"  Target queue: {args.queue_type}")
        print(f"  Location: {target_path}")
        logger.info(f"Successfully requeued {args.job_name} to {args.queue_type} queue")

        sys.exit(0)

    except GrabTaskNotFoundError as e:
        print(f"✗ Error: Task not found", file=sys.stderr)
        print(f"  {e.message}", file=sys.stderr)
        print(f"\nMake sure the job '{args.job_name}' has been executed by grabber '{args.grabber_name}'", file=sys.stderr)
        logger.error(f"Task not found: {e.message}")
        sys.exit(1)

    except GrabRerunError as e:
        print(f"✗ Error: Rerun operation failed", file=sys.stderr)
        print(f"  {e.message}", file=sys.stderr)
        logger.error(f"Rerun failed: {e.message}")
        sys.exit(1)

    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        logger.exception("Unexpected error during rerun")
        sys.exit(1)


if __name__ == "__main__":
    main()
