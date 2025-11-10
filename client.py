# client.py

import requests
import time
import os
import json

# --- Configuration ---
# The base URL of our running mock server.
SERVER_BASE_URL = "http://127.0.0.1:8000/v1"

# The local audio file you want to analyze.
# Make sure to create a dummy audio file (e.g., a short .mp3)
# and place its path here.
LOCAL_AUDIO_FILE = "path/to/your/test_audio.mp3"

# The audio file url you want to analyze.
# Make sure to create a dummy audio file (e.g., a short .mp3)
# and place its path here.
AUDIO_SOURCE_URL = "https://drive.google.com/uc?export=download&id=17_KyTouEQKI0eXAaupAh9yGN1v_6JmOa"


# --- Helper Functions for API Interaction ---

def upload_file(filepath: str) -> str | None:
    """
    Uploads a local file to the /uploads endpoint.
    Returns the uploadUrl if successful, otherwise None.
    """
    print(f"1. Uploading file: '{os.path.basename(filepath)}'...")

    upload_endpoint = f"{SERVER_BASE_URL}/uploads"

    if not os.path.exists(filepath):
        print(f"   [ERROR] File not found at path: {filepath}")
        return None

    with open(filepath, "rb") as f:
        try:
            files = {'file': (os.path.basename(filepath), f, 'audio/mpeg')}
            response = requests.post(upload_endpoint, files=files, timeout=30)

            # Check for HTTP errors
            response.raise_for_status()

            response_data = response.json()
            upload_url = response_data.get("uploadUrl")
            print(f"   [SUCCESS] File uploaded. URL: {upload_url}")
            return upload_url

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Failed to upload file: {e}")
            return None


def submit_job(upload_url: str) -> str | None:
    """
    Submits the uploadUrl to the /jobs endpoint to start analysis.
    Returns the jobId if successful, otherwise None.
    """
    print(f"2. Submitting job for analysis...")

    jobs_endpoint = f"{SERVER_BASE_URL}/jobs"
    payload = {"audioUrls": [upload_url]}

    try:
        response = requests.post(jobs_endpoint, json=payload, timeout=30)
        response.raise_for_status()

        response_data = response.json()
        job_id = response_data.get("id")
        print(f"   [SUCCESS] Job accepted. Job ID: {job_id}")
        return job_id

    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to submit job: {e}")
        return None

def submit_job_url(audio_url: str) -> str | None:
    print(f"1. Submitting job for analysis with URL: {audio_url}")
    jobs_endpoint = f"{SERVER_BASE_URL}/jobs"
    payload = {"audioUrls": [audio_url]}
    try:
        response = requests.post(jobs_endpoint, json=payload, timeout=30)
        response.raise_for_status()
        response_data = response.json()
        job_id = response_data.get("id")
        print(f"   [SUCCESS] Job accepted. Job ID: {job_id}")
        return job_id
    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to submit job: {e}")
        return None

def poll_for_result(job_id: str) -> dict | None:
    """
    Polls the /jobs/{jobId} endpoint until the job is completed or fails.
    Returns the final job object.
    """
    print(f"3. Polling for results (will check every 5 seconds)...")

    polling_endpoint = f"{SERVER_BASE_URL}/jobs/{job_id}"

    while True:
        try:
            response = requests.get(polling_endpoint, timeout=30)
            response.raise_for_status()

            job = response.json()
            status = job.get("status")

            print(f"   - Current job status: {status.upper()}")

            if status == "completed" or status == "failed":
                print(f"   [SUCCESS] Job finished.")
                return job

            time.sleep(5)  # Wait before polling again

        except requests.exceptions.RequestException as e:
            print(f"   [ERROR] Failed to poll for results: {e}")
            return None


def display_results(job: dict):
    """Formats and prints the final analysis report."""

    # !!! --- CRITICAL DEBUGGING STEP --- !!!
    # Print the raw job dictionary to see its exact structure and keys.
    print("\n--- Raw Job Data Received from Server ---")
    import json
    print(json.dumps(job, indent=2))
    print("---------------------------------------\n")
    # !!! ------------------------------------ !!!

    print("=" * 50)
    print("           FINAL ANALYSIS REPORT")
    print("=" * 50)
    print(f"Job ID: {job.get('id')}")
    print(f"Overall Status: {job.get('status', 'UNKNOWN').upper()}")

    # Check for the 'results' key, which is what our API returns
    if job.get('status') == 'completed' and job.get('results'):
        for result in job['results']:
            print("\n" + "-" * 40)
            # Use 'sourceUrl' as defined in our OpenAPI spec and server
            print(f"Analysis for: {result.get('sourceUrl')}")
            print(f"Result Status: {result.get('status')}")
            print("-" * 40)

            if result.get('status') == 'SUCCESS':
                # Print Summary
                summary = result.get('summary', {}).get('summary', 'Not available.')
                print(f"\n[SUMMARY]\n{summary}\n")

                # Print Detailed Sentiment
                print("[DETAILED SENTIMENT]")
                # Use 'sentiment' (camelCase) as the key
                sentiments = result.get('sentiment', {}).get('utterance_sentiments', [])
                if sentiments:
                    for s in sentiments:
                        print(
                            f"  - Utterance {s.get('utterance_index')}: {s.get('sentiment')} (Score: {s.get('score', 0.0):+.2f})")
                else:
                    print("  - Not available.")

                # Print Action Items
                print("\n[ACTION ITEMS]")
                # Use 'actionItems' (camelCase) as the key
                action_items = result.get('actionItems', {}).get('action_items', [])
                if action_items:
                    for item in action_items:
                        print(f"  - Task: {item.get('task')}")
                        print(f"    Owner: {item.get('owner')}")
                        print(f"    Context: \"{item.get('context')}\"")
                else:
                    print("  - No action items found.")
            else:
                # Use 'errorMessage' (camelCase) as the key
                print(f"  Error: {result.get('errorMessage')}")
    elif job.get('error'):
        print(f"Job failed with error: {job.get('error')}")

    print("\n" + "=" * 50)


# --- Main Application Logic ---

def main_upload_file():
    """The main function to run the client workflow."""
    # Step 1: Upload the file
    upload_url = upload_file(LOCAL_AUDIO_FILE)
    if not upload_url:
        return  # Stop if upload failed

    # Step 2: Submit the job
    job_id = submit_job(upload_url)
    if not job_id:
        return  # Stop if job submission failed

    # Step 3: Poll for the result
    final_job = poll_for_result(job_id)
    if not final_job:
        return  # Stop if polling failed

    # Step 4: Display the final report
    display_results(final_job)


def main_audio_url():
    """The main function to run the client workflow from a URL."""
    # Step 1: Submit the job directly with the URL
    job_id = submit_job_url(AUDIO_SOURCE_URL)
    if not job_id:
        return

    # Step 2: Poll for the result
    final_job = poll_for_result(job_id)
    if not final_job:
        return

    # Step 3: Display the final report
    display_results(final_job)
if __name__ == "__main__":
    main_audio_url()