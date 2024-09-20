## REQUIRED OUTPUT ###
# A list of version names -> v1.6, v.6_multimodal, v1.6_quantized, v1.5, v0.9, etc......
# A corresponding DataFrame?

import requests
from datetime import datetime
import pandas as pd
import json
from io import StringIO

from src.leaderboard_utils import process_df
from src.assets.text_content import REPO

def get_versions_data():
    """
    Read and process data from CSV files of all available versions hosted on GitHub. - https://github.com/clembench/clembench-runs

    Returns:
        versions_data:
            -
    """
    base_repo = REPO
    json_url = base_repo + "benchmark_runs.json"
    response = requests.get(json_url)

    # Check if the JSON file request was successful
    if response.status_code != 200:
        print(f"Failed to read JSON file: Status Code: {response.status_code}")
        return None, None, None, None

    json_data = response.json()
    versions = json_data['versions']

    version_names = sorted(
        [ver['version'] for ver in versions],
        key=lambda v: list(map(int, v[1:].split('_')[0].split('.'))),  # {{ edit_1 }}: Corrected slicing to handle 'v' prefix
        reverse=True
    )   

    # Get Last updated date of the latest version
    latest_version = version_names[0]
    latest_date = next(
        ver['date'] for ver in versions if ver['version'] == latest_version
    )
    formatted_date = datetime.strptime(latest_date, "%Y-%m-%d").strftime("%d %b %Y")  # {{ edit_1 }}: Updated date format

    # Get Versions data
    versions_data = {"latest": latest_version, "date": formatted_date}


    for version in version_names:
        if version.endswith("multimodal"):
            version_suffix = ""
        else:
            version_suffix = "_multimodal"

        mm_url = f"{base_repo}{version}{version_suffix}/results.csv"

        # Multimodal Data
        mm_response = requests.get(mm_url)
        if mm_response.status_code == 200:
            mm_df = pd.read_csv(StringIO(mm_response.text))
            mm_df = process_df(mm_df)
            mm_df = mm_df.sort_values(by=mm_df.columns[1], ascending=False)  # Sort by clemscore column
            versions_data[version+version_suffix] = mm_df
        else:
            print(f"Failed to read multimodal leaderboard CSV file for version: {version}: Status Code: {mm_response.status_code}. Please ignore this message if multimodal results are not available for this version")

    return versions_data


if __name__ == "__main__":
    versions_data = get_versions_data()
    print(versions_data.keys())
