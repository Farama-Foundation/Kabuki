import json
import os
import re
from collections import defaultdict

import gymnasium as gym
from google.cloud import storage  # pyright: ignore [reportGeneralTypeIssues]

from minari import list_remote_datasets
from minari.dataset.minari_dataset import parse_dataset_id
from minari.storage.hosting import find_highest_remote_version


filtered_datasets = defaultdict(defaultdict)
all_remote_datasets = list_remote_datasets()

for dataset_id in all_remote_datasets.keys():

    env_name, dataset_name, version = parse_dataset_id(dataset_id)

    if dataset_name not in filtered_datasets[env_name]:
        max_version = find_highest_remote_version(env_name, dataset_name)
        max_version_dataset_id = "-".join([env_name, dataset_name, f"v{max_version}"])
        filtered_datasets[env_name][dataset_name] = all_remote_datasets[
            max_version_dataset_id
        ]

for env_name, datasets in filtered_datasets.items():
    available_datasets = """
## Available Datasets
| Dataset ID | Description |
| ---------- | ----------- |
"""

    for i, (dataset_name, dataset_spec) in enumerate(datasets.items()):
        if i == 0:
            related_pages_meta = "firstpage:\n"
        elif i == len(datasets) - 1:
            related_pages_meta = "lastpage:\n"
        else:
            related_pages_meta = ""

        # Dataset Specs
        dataset_id = dataset_spec["dataset_id"]
        total_timesteps = dataset_spec["total_steps"]
        total_episodes = dataset_spec["total_episodes"]
        author = dataset_spec["author"]
        email = dataset_spec["author_email"]
        algo_name = dataset_spec["algorithm_name"]
        code = dataset_spec["code_permalink"]

        description = None
        if "description" in dataset_spec:
            description = dataset_spec["description"]

        # Add dataset id and description to main env page
        available_datasets += f"""| <a href="../{env_name}/{dataset_name}" title="{dataset_id}">{dataset_id}</a> | {description.split('. ')[0] if description is not None else ""} |
"""

        # Get image gif link if available
        img_path = f"{dataset_id}/_docs/_imgs/{dataset_id}.gif"
        storage_client = storage.Client.create_anonymous_client()
        bucket = storage_client.bucket(bucket_name="minari-datasets")

        img_exists = storage.Blob(bucket=bucket, name=img_path).exists(storage_client)

        img_link_str = None
        if img_exists:
            img_link_str = (
                f'<img src="https://storage.googleapis.com/minari-datasets/{dataset_id}/_docs/_imgs/{dataset_id}.gif" width="200" '
                'style="display: block; margin:0 auto"/>'
            )

        # Environment Specs
        env_spec = json.loads(dataset_spec["env_spec"])
        env_id = env_spec["id"]
        env = gym.make(env_id)

        action_space_table = env.action_space.__repr__().replace("\n", "")
        observation_space_table = env.observation_space.__repr__().replace("\n", "")

        env_page = f"""---
autogenerated:
title: {dataset_name.title()}
{related_pages_meta}---
# {dataset_name.title()}

{img_link_str if img_link_str is not None else ""}

## Description

{description if description is not None else ""}

## Dataset Specs

|    |    |
|----|----|
|Total Timesteps| `{total_timesteps}`|
|Total Episodes | `{total_episodes}` |
| Algorithm           | `{algo_name}`           |
| Author              | `{author}`              |
| Email               | `{email}`               |
| Code Permalink      | `{code}`                |
| download            | `minari.download_dataset("{dataset_id}")` |


## Environment Specs

|    |    |
|----|----|
|ID| `{env_id}`|
| Action Space | `{re.sub(' +', ' ', action_space_table)}` |
| Observation Space | `{re.sub(' +', ' ', observation_space_table)}` |

"""

        dataset_doc_path = os.path.join(
            os.path.dirname(__file__), "..", "datasets", env_name
        )

        if not os.path.exists(dataset_doc_path):
            os.makedirs(dataset_doc_path)

        dataset_md_path = os.path.join(
            dataset_doc_path,
            dataset_name + ".md",
        )

        file = open(dataset_md_path, "w", encoding="utf-8")
        file.write(env_page)
        file.close()

    env_page_path = os.path.join(
        os.path.dirname(__file__), "..", "datasets", f"{env_name}.md"
    )
    file = open(env_page_path, "a", encoding="utf-8")
    file.write(available_datasets)
    file.close()
