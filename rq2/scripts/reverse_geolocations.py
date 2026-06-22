import json
import os
import time
import requests

API_KEY = "YOUR_API_KEY"

INPUT_PATH = "repos_filtered_data_with_valid_locations.json"
CITY_FILE = "unique-filtered-cities-with-countries.json"

OUTPUT_PATH = "final_all_locations.json"
CACHE_PATH = "geo_cache.json"

CHECKPOINT_PATH = "checkpoint.txt"

BATCH_SIZE = 50
SLEEP = 0.25
MAX_RETRIES = 3


def reverse_geocode(lat, lon):
    url = "https://api.geoapify.com/v1/geocode/reverse"

    params = {
        "lat": lat,
        "lon": lon,
        "apiKey": API_KEY,
        "format": "json"
    }

    for i in range(MAX_RETRIES):
        try:
            r = requests.get(url, params=params)
            if r.status_code == 200:
                data = r.json()
                if data.get("results"):
                    res = data["results"][0]
                    return {
                        "country": res.get("country"),
                        "country_code": res.get("country_code"),
                        "city": res.get("city"),
                        "formatted": res.get("formatted")
                    }
        except Exception as e:
            print("API error:", e)

        time.sleep(1.5 * (i + 1))

    return None


def load_cache():
    if os.path.exists(CACHE_PATH):
        return json.load(open(CACHE_PATH))
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


# def load_city_cache():
#     if not os.path.exists(CITY_FILE):
#         return {}

#     data = json.load(open(CITY_FILE))

#     cache = {}
#     for r in data:
#         key = (r.get("location_normalized", "").strip().lower(),
#                r.get("name", "").strip().lower())

#         cache[key] = {
#             "country": r.get("country"),
#             "country_code": r.get("country_code"),
#             "city": r.get("city"),
#             "formatted": r.get("formatted")
#         }

#     print(f"City cache loaded: {len(cache)}")
#     return cache


def transform_record(rec, api_cache):
    p = rec.get("main_contributor_profile", {})

    lat = p.get("location_lat")
    lon = p.get("location_lon")

    rec_out = {
        "name": rec.get("name"),
        "main_contributor": rec.get("main_contributor"),
        "location_type": p.get("location_type"),
        "location_normalized": p.get("location_normalized"),
        "location_lat": lat,
        "location_lon": lon,
        "country": None,
        "country_code": None,
        "city": None,
        "formatted": None
    }

    if lat is None or lon is None:
        return rec_out

    key_api = f"{lat},{lon}"

    if rec_out["location_type"] == "country":
        rec_out["country"] = rec_out["location_normalized"]
        return rec_out

    if key_api in api_cache:
        rec_out.update(api_cache[key_api])
        return rec_out

    geo = reverse_geocode(lat, lon)
    time.sleep(SLEEP)

    if geo:
        rec_out.update(geo)
        api_cache[key_api] = geo

    return rec_out


def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        return int(open(CHECKPOINT_PATH).read().strip())
    return 0


def save_checkpoint(i):
    with open(CHECKPOINT_PATH, "w") as f:
        f.write(str(i))


def main():
    repos = json.load(open(INPUT_PATH))
    print("Loaded:", len(repos))

    # city_cache = load_city_cache()
    api_cache = load_cache()

    start = load_checkpoint()
    print("Resuming from:", start)

    # load existing output if restart
    if os.path.exists(OUTPUT_PATH):
        output = json.load(open(OUTPUT_PATH))
    else:
        output = []

    for i in range(start, len(repos)):

        rec = transform_record(repos[i], api_cache)

        output.append(rec)

        # checkpoint every batch
        if i % BATCH_SIZE == 0:
            with open(OUTPUT_PATH, "w") as f:
                json.dump(output, f, indent=2)

            save_checkpoint(i)

            save_cache(api_cache)

            print(f"Progress: {i}/{len(repos)}")

    # final write
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    save_checkpoint(len(repos))
    save_cache(api_cache)

    print("\nDONE")
    print("Final size:", len(output))


if __name__ == "__main__":
    main()