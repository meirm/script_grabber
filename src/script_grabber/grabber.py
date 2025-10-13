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

import os
import sys
import time
from pathlib import Path
import shutil
import subprocess
import argparse
import logging
import signal
from typing import List, Optional
from datetime import datetime, timedelta
import time
import signal
# Import local modules here.
from .grabexceptions import GrabLockError, GrabRerunError, GrabTaskNotFoundError
__author__ = "Meir Michanie"
__email__ = "meirm@riunx.com"
__version__ = "0.1.0"

__all__ = [
    # List exported symbols here.
]



class GrabError(Exception):
    pass


class GrabTimeoutError(GrabError):
    pass


class Grabber:
    def __init__(
        self,
        name: str, # name of the grabber instance
        clusterpath: str, # path to the cluster directory
        job_timeout: int = None, # maximum time allowed for a job to run before timing out
        ctrlqueue: str = None, # path to the grabber's control queue
        queue: str = None, # path to the common queue
        spool: str = None, # path to the grabber's spool
        spoollog: str = None, # path to the spool log directory
        varlock: str = None, # path to the varlock directory
        logfile: str = None, # path to the grabber's log file
        
        sleep_time: int = None # time to sleep between iterations of the loop
        ):
        """
        Initializes a Grabber object.
        :param name: Name of the grabber instance.
        :param clusterpath: Path to the cluster directory.
        :param ctrlqueue: Path to the grabber's control queue (optional).
        :param queue: Path to the common queue (optional).
        :param spool: Path to the grabber's spool (optional).
        :param spoollog: Path to the spool log directory (optional).
        :param varlock: Path to the varlock directory (optional).
        :param logfile: Path to the grabber's log file (optional).
        :param job_timeout: Maximum time allowed for a job to run before timing out (optional).
        :param sleep_time: Time to sleep between iterations of the loop (optional).
        """
        
        self.grabberName = name
        self.clusterpath = clusterpath
        self.ctrlqueue = ctrlqueue
        self.queue = queue
        self.spool = spool
        self.spoollog = spoollog
        self.varlock = varlock
        self.logfile = logfile
        self.job_timeout = job_timeout
        self.sleep_time = sleep_time
        self.defaults()
        self.ensure_dirs()
        logging.basicConfig(
            filename=os.path.join(self.clusterpath, "log", f"{self.grabberName}.log"),
            level=logging.DEBUG,
            format="[%(asctime)s][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger("grabber")
        self.is_running = True
        self.is_paused = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.handle_sigint)
        signal.signal(signal.SIGUSR1, self.handle_usr1)
        signal.signal(signal.SIGUSR2, self.handle_usr2)

    def handle_sigint(self, signum, frame):
        self.is_running = False
        self.is_paused = False
        #remove lock
        lockfile_path = os.path.join(self.varlock, f"{self.grabberName}.lock")
        if os.path.exists(lockfile_path):
            os.remove(lockfile_path)

        self.logger.info("Received SIGTERM. Stopping jobs, renaming to interrupted and exiting.")
        # Rename jobs to interrupted here
        exit(0)
        
    def handle_usr1(self, signum, frame):
        print("Received USR1. Dumping status:")
        # Dump status here
        
    def handle_usr2(self, signum, frame):
        if self.is_paused:
            self.is_paused = False
            self.logger.info("Received USR2. Resuming polling.")
        else:
            self.is_paused = True
            self.logger.info("Received USR2. Pausing polling.")
        

    def defaults(self):
        self.ctrlqueue = self.ctrlqueue or f"{self.clusterpath}/ctrl/{self.grabberName}"
        self.queue = self.queue or f"{self.clusterpath}/queue"
        self.spool = self.spool or f"{self.clusterpath}/spool/{self.grabberName}"
        self.spoollog = self.spoollog or f"{self.clusterpath}/log"
        self.varlock = self.varlock or f"{self.clusterpath}/varlock"
        self.logfile = self.logfile or f"{self.spoollog}/{self.grabberName}.log"
        self.job_timeout = self.job_timeout or 3600  # 1 hour by default
        self.sleep_time = self.sleep_time or 10  # 10 seconds by default

    def run(self):
        """
        Runs the grabber in an endless loop, sleeping for `self.sleep_time` seconds
        between each iteration.
        """
        lockfile_path = os.path.join(self.varlock, f"{self.grabberName}.lock")
        if os.path.exists(lockfile_path):
            GrabLockError(f"Grabber {self.grabberName} already running or stalled, remove {lockfile_path} and try again")
        with open(lockfile_path, "w") as lockfile:
                lockfile.write(str(os.getpid()))
        while self.is_running:
            # Try to acquire the lockfile
            if self.is_paused:
                time.sleep(self.sleep_time)
                continue
        
            

            # Grab a job from the queue
            self.running_job_path = None
            self.running_job_path = self.grab_job()
            if self.running_job_path:
                self.run_job()


    def ensure_dirs(self) -> None:
        """Ensure that all required directories exist."""
        os.makedirs(self.spool, exist_ok=True)
        os.makedirs(self.ctrlqueue, exist_ok=True)
        os.makedirs(self.queue, exist_ok=True)
        os.makedirs(os.path.join(self.clusterpath, "log"), exist_ok=True)
        os.makedirs(self.varlock, exist_ok=True)
        os.makedirs(os.path.join(self.clusterpath, "temp"), exist_ok=True)

    def grab_job(self) -> Optional[str]:
        """Grab a job from the queue if there is one available."""
        for queue in [self.ctrlqueue, self.queue]:
            file_list = os.listdir(queue)
            if file_list:
                self.job_file = file_list[0]
                job_file_path = os.path.join(queue, self.job_file)

                job_file_move_path = os.path.join(
                    self.spool, f"{self.job_file}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                )

                # Move the job file to the spool directory
                try:
                    shutil.move(job_file_path, job_file_move_path)
                except FileNotFoundError:
                    # File was removed by another grabber before we could move it
                    continue

                # Rename the job file to indicate that it is now running
                running_job_path = os.path.join(
                    self.spool, f"{self.job_file}-{datetime.now().strftime('%Y%m%d%H%M%S')}-RUNNING"
                )
                os.rename(job_file_move_path, running_job_path)

                # Ensure that the running job file is executable
                os.chmod(running_job_path, 0o755)

                self.logger.info(f"{self.grabberName} running {self.job_file}")

                return running_job_path

        return None

    def run_job(self) -> None:
        # Convert running_job_path to a Path object
        self.running_job_path = Path(self.running_job_path)

        # Ensure the job file exists before trying to execute it
        if not self.running_job_path.exists():
            self.logger.error(f"Job file {self.running_job_path} does not exist.")
            return
        # Open the job file
        try:
            # Execute the job
            process = subprocess.run([sys.executable, str(self.running_job_path)],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        cwd=str(self.clusterpath))
        except FileNotFoundError:
            # Failed to open the file, it was already picked up by another process
            return

        # Determine the appropriate destination for the job file based on the exit code
        done_job_path = str(self.running_job_path).replace("-RUNNING","-DONE")
        timeout_job_path = str(self.running_job_path).replace("-RUNNING","-TIMEOUT")
        failed_job_path = str(self.running_job_path).replace("-RUNNING","-FAILED")
        log_path = Path(self.spoollog) / f"{self.job_file}.log"
        if process.returncode == 0:
            dest_path = done_job_path
        elif process.returncode == 124:
            dest_path = timeout_job_path
        else:
            dest_path = failed_job_path

        # Move the job file to the appropriate destination
        shutil.move(str(self.running_job_path), str(dest_path))

        # Write the stdout and stderr to the their respective log files
        with open(str(log_path.with_suffix(".out")), "wb") as f:
            f.write(process.stdout)
        with open(str(log_path.with_suffix(".err")), "wb") as f:
            f.write(process.stderr)
        # Write the log file
        with open(str(log_path), "a") as f:
            f.write(f"{self.job_file},{datetime.now().strftime('%Y%m%d%H%M%S')},"
                    f"ExitCode({process.returncode})\n")

    def rerun_task(self, job_name: str, target_queue: str = "common") -> str:
        """
        Rerun a completed task by copying it to the specified queue.

        :param job_name: Base name of the job to rerun (e.g., "test_job.py")
        :param target_queue: Target queue type - "common" or "control" (default: "common")
        :return: Path to the requeued job file
        :raises GrabTaskNotFoundError: If the specified job cannot be found in spool
        :raises GrabRerunError: If the rerun operation fails
        """
        self.logger.info(f"Attempting to rerun task: {job_name} to {target_queue} queue")

        # Search for completed job files in spool directory
        # Pattern: {job_name}-{timestamp}-(DONE|FAILED|TIMEOUT)
        job_base_name = job_name.replace('.py', '')
        search_pattern = f"{job_base_name}-*"

        matching_jobs = []
        for filename in os.listdir(self.spool):
            if filename.startswith(job_base_name) and filename.endswith(('-DONE', '-FAILED', '-TIMEOUT')):
                matching_jobs.append(filename)

        if not matching_jobs:
            error_msg = f"Task '{job_name}' not found in spool directory: {self.spool}"
            self.logger.error(error_msg)
            raise GrabTaskNotFoundError(error_msg)

        # Use the most recent job (last in sorted list)
        matching_jobs.sort()
        source_job = matching_jobs[-1]
        source_path = os.path.join(self.spool, source_job)

        self.logger.info(f"Found job to rerun: {source_job}")

        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(self.clusterpath, "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Copy job file to temp directory with original name
        temp_path = os.path.join(temp_dir, job_name)
        try:
            shutil.copy2(source_path, temp_path)
            self.logger.info(f"Copied job to temp directory: {temp_path}")
        except Exception as e:
            error_msg = f"Failed to copy job to temp directory: {e}"
            self.logger.error(error_msg)
            raise GrabRerunError(error_msg)

        # Determine target queue path
        if target_queue == "control":
            queue_path = self.ctrlqueue
        elif target_queue == "common":
            queue_path = self.queue
        else:
            error_msg = f"Invalid queue type: {target_queue}. Must be 'common' or 'control'"
            self.logger.error(error_msg)
            raise GrabRerunError(error_msg)

        # Move job from temp to target queue (atomic operation)
        target_path = os.path.join(queue_path, job_name)
        try:
            shutil.move(temp_path, target_path)
            self.logger.info(f"Rerun successful: {source_job} -> {target_queue} queue ({target_path})")
        except Exception as e:
            error_msg = f"Failed to move job to queue: {e}"
            self.logger.error(error_msg)
            raise GrabRerunError(error_msg)

        return target_path

def  main():
     # Parse command-line arguments.
        parser = argparse.ArgumentParser(description="A job grabber for a cluster.")
        parser.add_argument("name", help="the name of this grabber")
        parser.add_argument("cluster_path", help="the path to the cluster directory")
        parser.add_argument("--job-timeout", type=int, default=60, help="the number of seconds after which a job will be terminated (default: %(default)s)")
        args = parser.parse_args()

        grabber = Grabber(args.name, args.cluster_path, args.job_timeout)
        grabber.run()

if __name__ == "__main__":
       main()
