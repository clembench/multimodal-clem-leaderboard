import os
import pandas as pd
import requests
import json
from io import StringIO
from datetime import datetime

from src.assets.text_content import REPO

def get_github_data():
    """
    Read and process data from CSV files hosted on GitHub. - https://github.com/clembench/clembench-runs

    Returns:
        github_data (dict): Dictionary containing:
            - "text": List of DataFrames for each version's textual leaderboard data.
            - "multimodal": List of DataFrames for each version's multimodal leaderboard data.
            - "date": Formatted date of the latest version in "DD Month YYYY" format.
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

    # Get Leaderboard data - for text-only + multimodal
    github_data = {}

    mm_dfs = []
    mm_date = ""
    mm_flag = True
    for version in version_names:
        # Check if version ends with 'multimodal' before constructing the URL
        mm_suffix = "_multimodal" if not version.endswith('multimodal') else ""
        mm_url = f"{base_repo}{version}{mm_suffix}/results.csv"  # {{ edit_1 }}: Conditional suffix for multimodal
        mm_response = requests.get(mm_url)
        if mm_response.status_code == 200:
            df = pd.read_csv(StringIO(mm_response.text))
            df = process_df(df)
            df = df.sort_values(by=df.columns[1], ascending=False) # Sort by clemscore column
            mm_dfs.append(df)
            if mm_flag:
                mm_date = next(ver['date'] for ver in versions if ver['version'] == version)
                mm_date = datetime.strptime(mm_date, "%Y-%m-%d").strftime("%d %b %Y")
                mm_flag = False

    github_data["multimodal"] = mm_dfs
    github_data["date"] = mm_date

    return github_data


def process_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Process dataframe:
    - Convert datatypes to sort by "float" instead of "str"
    - Remove repetition in model names
    - Update column names

    Args:
        df: Unprocessed Dataframe (after using update_cols)

    Returns:
        df: Processed Dataframe
    """

    # Convert column values to float, apart from the model names column
    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Remove repetition in model names
    df[df.columns[0]] = df[df.columns[0]].str.replace('-t0.0', '', regex=True)
    df[df.columns[0]] = df[df.columns[0]].apply(lambda x: '--'.join(set(x.split('--'))))

    # Update column names
    custom_column_names = ['Model', 'Clemscore', '% Played', 'Quality Score']
    for i, col in enumerate(df.columns[4:]):  # Start Capitalizing from the 5th column
        parts = col.split(',')
        custom_name = f"{parts[0].strip().capitalize()} {parts[1].strip()}"
        custom_column_names.append(custom_name)

    # Rename columns
    df.columns = custom_column_names

    return df


def query_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Filter the dataframe based on the search query.

    Args:
        df (pd.DataFrame): Unfiltered dataframe.
        query (str): A string of queries separated by ";".
    Returns:
        pd.DataFrame: Filtered dataframe containing searched queries in the 'Model' column.
    """
    if not query.strip():  # Reset Dataframe if empty query is passed
        return df

    queries = [q.strip().lower() for q in query.split(';') if q.strip()]  # Normalize and split queries

    # Filter dataframe based on queries in 'Model' column
    filtered_df = df[df['Model'].str.lower().str.contains('|'.join(queries))]

    return filtered_df