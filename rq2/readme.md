# RQ2

This folder contains all collected data and the scripts used to collect and process the data for RQ2.

## /data/

* `repos_with_locations.json`: A list of repositories where the main contributor has declared a valid location.
* `normalized_location_not_found.json`: A list of repositories where the main contributor has declared a location that could not be resolved by Geoapify.

## /scripts/

* `sample_selection.py`: Script for selecting a random sample of 10% of repositories from the complete original dataset.
* `mine-art-metadata.py`: Script used to collect metadata for each selected repository, including the repository README, the main contributor, and the contributor's location and bio.
* `geolocations.py`: Script used to query Geoapify and convert user-defined locations into latitude and longitude coordinates.
* `reverse_geolocations.py`: Script used to perform reverse geocoding with Geoapify and identify the country associated with previously obtained coordinates.
* `locationIndex_script.js`: Script used to simplify the processed location data.
* Observable Notebook: https://observablehq.com/@sparkrew/art-in-swh-rq2
  This notebook contains the code used to clean the data, generate the JSON files used for the map, and create the map and plot visualizations.
