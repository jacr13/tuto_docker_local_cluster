#!/usr/bin/env python3

import getpass
import os
import subprocess
from datetime import datetime, timedelta

UG_SLURM_PARSE_ARGS_PATH = "/usr/local/bin/ug_slurm_parse_args.py"
UG_SLURM_USAGE_PATH = "/usr/local/bin/ug_slurm_usage_per_user.py"
UG_NODE_SUMMARY_PATH = "/usr/local/sbin/ug_getNodeCharacteristicsSummary.py"
SLURMPARTITIONS_PATH = "/usr/local/sbin/slurmpartitions.py"

REFERENCE_YEAR = datetime.today().year
YEAR_START = f"{REFERENCE_YEAR}-01-01"
YEAR_END = f"{REFERENCE_YEAR+1}-01-01"

PI_NAME = "kalousis"
DEFAULT_PARTITION = "private-kalousis-gpu"
CLUSTERS = ["baobab", "yggdrasil", "bamboo"]
OUTPUT_ENV_PATH = os.path.join(os.path.expanduser("~"), ".my_hpc_usage.env")
DMML_HPC_USERS = 13
VERBOSE = True
UPDATE_INTERVALE = 24 * 60  # minutes


def run_cmd(cmd):
    """
    Run any command and return stdout as a string.
    """
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def get_year_capacity():
    # Capacity per cluster
    total = 0
    info = {}
    return total, info


def get_team_and_personal_usage(user):
    """
    Executes the kalousis usage command and returns:
        team_usage: total usage across all users
        user_usage: usage for the given user login
        info: dict[cluster][login] -> used_hours
    """
    cmd = [
        "ug_slurm_usage_per_user.py",
        "--pi",
        "kalousis",
        "--all-users",
        "--start",
        "2025-01-01",
        "--end",
        "2026-01-01",
    ]

    output = run_cmd(cmd)

    info = {}

    for line in output.splitlines():
        line = line.strip()
        if (
            not line
            or line.startswith("----")
            or line.startswith("Cluster/")
            or line.startswith("Cluster")
            or line.startswith("Usage reported")
            or line.startswith("Total usage:")
            or line.startswith("TRES")
        ):
            continue

        parts = line.split()
        if len(parts) < 3:
            continue

        cluster = parts[0]
        login = parts[1]
        used_str = parts[-1]

        try:
            used = int(used_str.replace(",", ""))
        except ValueError:
            continue

        cluster_dict = info.setdefault(cluster, {})
        cluster_dict[login] = cluster_dict.get(login, 0) + used

    team_total = sum(
        used for cluster_dict in info.values() for used in cluster_dict.values()
    )

    user_total = sum(info[c].get(user, 0) for c in info)

    return team_total, user_total, info


def main():
    user = getpass.getuser()
    now_dt = datetime.now()
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

    env_data = {}

    team_total, user_total, info = get_team_and_personal_usage(user)

    print(f"User: {user}")
    print(f"Team total usage (hours): {team_total}")
    print(f"User total usage (hours): {user_total}")
    print(f"Usage details by cluster and user: {info}")


if __name__ == "__main__":
    main()
