import requests
import os
import time
import json
from requests.structures import CaseInsensitiveDict
from dotenv import load_dotenv # type: ignore

load_dotenv()
# Geoapify API key
apiKey = ""
# Time to wait between attempts (in seconds)
timeout = 3
# How many times to try checking the results
maxAttempts = 6
BATCH_SIZE = 30
MIN_REQUEST_INTERVAL = 0.21


# code for geocode_batch and fetch_results found here: https://www.geoapify.com/tutorial/batch-geocoding-python/

# expects one String unstructured address
# returns a json array with a single geoapi object for the address
def geocode(address, last_request_time):
    elapsed = time.time() - last_request_time
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    url = f"https://api.geoapify.com/v1/batch/geocode/search?apiKey={apiKey}"
    response = requests.post(url, json=[address])
    request_time = time.time()
    if response.status_code != 202:
        print("Failed to create the job. Check the input data.")
        return None, request_time
    jobId = response.json()["id"]
    results_url = f"{url}&id={jobId}"
    print(f"Job submitted. Waiting for results (Job ID: {jobId})...")
    time.sleep(timeout)
    return fetch_results(results_url, attempt=0), request_time

# expects an array of Strings unstructured addresses
# returns an array of json geoapi objects, one per address
def geocode_batch(addresses):
    url = f"https://api.geoapify.com/v1/batch/geocode/search?apiKey={apiKey}"
    response = requests.post(url, json=addresses)
    if response.status_code != 202:
        print("Failed to create the job. Check the input data.")
        return
    jobId = response.json()["id"]
    results_url = f"{url}&id={jobId}"
    print(f"Job submitted. Waiting for results (Job ID: {jobId})...")
    time.sleep(timeout)
    return fetch_results(results_url, attempt=0)

def fetch_results(url, attempt):
    response = requests.get(url)
    if response.status_code == 200:
        print("Job completed.")
        return response.json()
    elif response.status_code == 202 and attempt < maxAttempts:
        print(f"Still processing... (Attempt {attempt + 1})")
        time.sleep(timeout)
        return fetch_results(url, attempt + 1)
    else:
        print("Results not ready. You can check later at:")
        print(url)
        print(response.json())
        return response.json()

def is_valid_location(loc):
    return loc is not None and loc.strip().lower() not in {"", "none", "null", "unknown"}

# expects a GHdatafile JSON file, which should be an array of JSON objects similar to the example found in sample-rq2-data.json
def getGHloc(GHdatafile):
    filename = GHdatafile.split(".json")
    destfilename = filename[0] + "with_locations.json"

    with open(GHdatafile, 'r') as file:
        GHdata = json.load(file)

    # Resume from existing output file if it exists
    processed_records = []
    processed_names = set()
    if os.path.exists(destfilename):
        with open(destfilename, 'r') as f:
            processed_records = json.load(f)
            processed_names = {r["name"] for r in processed_records}
        print(f"Resuming: {len(processed_records)} records already processed.")

    last_request_time = 0
    for batch_start in range(0, len(GHdata), BATCH_SIZE):
        batch = GHdata[batch_start:batch_start + BATCH_SIZE]
        new_in_batch = 0

        for repo in batch:
            if repo["name"] in processed_names:
                continue
            raw_loc = repo["main_contributor_profile"]["location"]
            if is_valid_location(raw_loc):
                loc, last_request_time = geocode(raw_loc, last_request_time)
                if loc is None or "status" in loc:
                    repo["main_contributor_profile"]["location_normalized"] = "time-out"
                    repo["main_contributor_profile"]["location_type"] = "time-out"
                    repo["main_contributor_profile"]["location_lat"] = "time-out"
                    repo["main_contributor_profile"]["location_lon"] = "time-out"
                else:
                    if "result_type" in loc[0]:
                        repo["main_contributor_profile"]["location_type"] = loc[0]["result_type"]
                        if loc[0]["result_type"] == "city":
                            repo["main_contributor_profile"]["location_normalized"] = loc[0]["city"]
                        elif loc[0]["result_type"] == "country":
                            repo["main_contributor_profile"]["location_normalized"] = loc[0]["country"]
                        elif loc[0]["result_type"] == "state":
                            repo["main_contributor_profile"]["location_normalized"] = loc[0]["formatted"]
                        elif loc[0]["result_type"] == "county":
                            repo["main_contributor_profile"]["location_normalized"] = loc[0]["formatted"]
                        elif loc[0]["result_type"] == "district":
                            repo["main_contributor_profile"]["location_normalized"] = loc[0]["formatted"]
                        else:
                            repo["main_contributor_profile"]["location_normalized"] = "not_found"
                    else:
                        repo["main_contributor_profile"]["location_normalized"] = "not_found"
                        repo["main_contributor_profile"]["location_type"] = "not_found"
                        repo["main_contributor_profile"]["location_lat"] = "not_found"
                        repo["main_contributor_profile"]["location_lon"] = "not_found"
                    if "lon" in loc[0]:
                        repo["main_contributor_profile"]["location_lat"] = loc[0]["lat"]
                        repo["main_contributor_profile"]["location_lon"] = loc[0]["lon"]
            else:
                repo["main_contributor_profile"]["location_normalized"] = "none"
                repo["main_contributor_profile"]["location_type"] = "none"
                repo["main_contributor_profile"]["location_lat"] = "none"
                repo["main_contributor_profile"]["location_lon"] = "none"

            processed_records.append(repo)
            processed_names.add(repo["name"])  # keep set in sync
            new_in_batch += 1

        batch_num = batch_start // BATCH_SIZE + 1
        if new_in_batch > 0:
            with open(destfilename, 'w') as json_file:
                json.dump(processed_records, json_file)
            print(f"Batch {batch_num} written ({len(processed_records)}/{len(GHdata)} records).")
        else:
            print(f"Batch {batch_num} skipped (already processed).")

def main():
    getGHloc("/Tmp/spark/rq2_art_repo_data/updated/repos_data.json")

if __name__ == "__main__":
    main()
    