"""Background worker — polls job queue and processes tasks."""

from __future__ import annotations

import logging
import os
import time

from db.connection import init_db
from db.jobs_store import claim_next_job, complete_job, fail_job
from worker.processor import process_job

POLL_SECONDS = float(os.environ.get("WORKER_POLL_SECONDS", "2"))


def run_once() -> bool:
    job = claim_next_job()
    if job is None:
        return False
    log = logging.getLogger("worker")
    log.info("Processing job %s type=%s", job["job_id"], job["job_type"])
    try:
        result = process_job(job)
        complete_job(job["job_id"], result)
        log.info("Completed job %s", job["job_id"])
    except Exception as exc:
        fail_job(job["job_id"], str(exc))
        log.exception("Failed job %s: %s", job["job_id"], exc)
    return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    init_db()
    logging.getLogger("worker").info("Worker started (poll=%ss)", POLL_SECONDS)
    while True:
        processed = run_once()
        if not processed:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
