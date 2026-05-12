import json
import os
import urllib.parse
import urllib.request

from bot_script import run_bot

APPS_SCRIPT_URL = os.environ["APPS_SCRIPT_URL"]


def call_api(action, params=None):
    url = f"{APPS_SCRIPT_URL}?action={action}"
    if params:
        for k, v in params.items():
            url += f"&{urllib.parse.quote(str(k))}={urllib.parse.quote(str(v))}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    print("Checking pending jobs...")
    result = call_api("getPendingJobs")
    jobs = result.get("jobs", [])

    if not jobs:
        print("No pending jobs. Done.")
        return

    print(f"Found {len(jobs)} job(s)")

    for job in jobs:
        job_id = job.get("job_id")
        print(f"\nRunning job {job_id}: {job}")

        bot_result = run_bot(
            url=os.environ.get("TARGET_URL"),
            date=job.get("booking_date"),
            duty=job.get("duty"),
            name=job.get("name"),
        )

        status = bot_result.get("status", "ERROR")
        call_api("markJobDone", {"job_id": job_id, "result_status": status})
        print(f"Job {job_id} marked as {status}")


if __name__ == "__main__":
    main()
