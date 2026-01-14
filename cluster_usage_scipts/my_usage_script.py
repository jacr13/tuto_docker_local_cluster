#!/usr/bin/env python3

import ast
import getpass
import os
import re
import subprocess
from datetime import datetime, timedelta

# paths to external scripts just for reference
# UG_SLURM_PARSE_ARGS_PATH = "/usr/local/bin/ug_slurm_parse_args.py"
# UG_SLURM_USAGE_PATH = "/usr/local/bin/ug_slurm_usage_per_user.py"
# UG_NODE_SUMMARY_PATH = "/usr/local/sbin/ug_getNodeCharacteristicsSummary.py"
# SLURMPARTITIONS_PATH = "/usr/local/sbin/slurmpartitions.py"

REFERENCE_YEAR = datetime.today().year
YEAR_START = f"{REFERENCE_YEAR}-01-01"
YEAR_END = f"{REFERENCE_YEAR+1}-01-01"

PI_NAME = "kalousis"
DEFAULT_PARTITION = "private-kalousis-gpu"
CLUSTERS = ["baobab", "yggdrasil", "bamboo"]
OUTPUT_ENV_PATH = os.path.join(os.path.expanduser("~"), ".my_hpc_usage.env")
DMML_HPC_USERS = 13
VERBOSE = True
UPDATE_INTERVALE = 10  # minutes, only runs on new login or reload of .bashrc


def run_cmd(cmd):
    """
    Run any command and return stdout as a string.
    """
    cmd_str = " ".join(cmd)
    result = subprocess.run(
        cmd_str,
        shell=True,
        check=True,
        capture_output=True,
        text=True,
        executable="/bin/bash",
    )
    return result.stdout


def get_year_capacity():
    cmd = [
        "ug_getNodeCharacteristicsSummary.py",
        "--summary",
        "-p",
        "private-kalousis-gpu",
        "-c",
    ]

    total_cpuhours = 0
    info = {}

    for cluster in CLUSTERS:
        cluster_cmd = cmd + [cluster]
        output = run_cmd(cluster_cmd)

        match = re.search(r"CPUhours per year:\s*([\d.]+)M", output)
        if match:
            info[cluster] = int(float(match.group(1)) * 1_000_000)
        else:
            info[cluster] = 0
        total_cpuhours += info[cluster]

    # Extract reported total from summary (optional consistency check)
    try:
        output = run_cmd(cmd + ["{baobab,yggdrasil,bamboo}"])
        summary_match = re.search(r"CPUhours per year:\s*([\d.]+)M", output)
        if summary_match:
            reported_total = int(float(summary_match.group(1)) * 1_000_000)
        else:
            reported_total = 0
    except subprocess.CalledProcessError:
        reported_total = 0

    return total_cpuhours, info, reported_total


def get_team_and_personal_usage(user):
    """
    Executes the kalousis usage command and returns:
        team_usage: total usage across all users
        user_usage: usage for the given user login
        info: dict[cluster][login] -> used_hours
        users: dict[login][cluster] -> used_hours
    """
    cmd = [
        "ug_slurm_usage_per_user.py",
        "--pi",
        "kalousis",
        "--all-users",
        "--start",
        YEAR_START,
        "--end",
        YEAR_END,
    ]

    output = run_cmd(cmd)

    info = {}  # cluster -> login -> usage
    users = {}  # login -> cluster -> usage

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

        # cluster -> user
        info.setdefault(cluster, {})
        info[cluster][login] = info[cluster].get(login, 0) + used

        # user -> cluster
        users.setdefault(login, {})
        users[login][cluster] = users[login].get(cluster, 0) + used

    team_total = sum(
        used for cluster_dict in info.values() for used in cluster_dict.values()
    )

    user_total = sum(users.get(user, {}).values())

    return team_total, user_total, info, users


def main():
    user = getpass.getuser()
    now_dt = datetime.now()
    now = now_dt.strftime("%Y-%m-%dT%H:%M:%S")

    env_data = {}

    if os.path.exists(OUTPUT_ENV_PATH):
        with open(OUTPUT_ENV_PATH, "r", encoding="ascii") as f:
            existing_lines = f.readlines()

        env_data = {
            key.strip(): value.strip()
            for key, value in (
                line.split("=", 1) for line in existing_lines if "=" in line
            )
        }
        for key, value in env_data.items():
            try:
                env_data[key] = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                pass

    last_update_raw = env_data.get("LAST_HPC_USAGE_UPDATE")
    last_update_dt = None
    if last_update_raw:
        try:
            last_update_dt = datetime.fromisoformat(str(last_update_raw))
        except ValueError:
            last_update_dt = None

    update_needed = (
        not env_data
        or last_update_dt is None
        or (now_dt - last_update_dt) > timedelta(minutes=UPDATE_INTERVALE)
    )

    if update_needed:
        capacity_total, capacity_info, capacity_total_reported = get_year_capacity()
        team_usage, my_usage, usage_info, users_info = get_team_and_personal_usage(user)
        env_data = {
            "HPC_MY_USAGE": my_usage,
            "HPC_TEAM_USAGE": team_usage,
            "HPC_TEAM_BUDGET_YEAR": capacity_total,
            "HPC_TEAM_BUDGET_BY_CLUSTER": capacity_info,
            "HPC_USERS_INFO": users_info,
            "HPC_TEAM_BUDGET_YEAR_REPORTED": capacity_total_reported,
            "HPC_MY_PCT": 0,
            "HPC_TEAM_PCT": 0,
            "HPC_MAX_PCT": 100 // DMML_HPC_USERS,
            "LAST_HPC_USAGE_UPDATE": now,
        }

    # Compute percentages
    capacity_value = float(env_data.get("HPC_TEAM_BUDGET_YEAR", 1) or 1)
    my_usage_value = float(env_data.get("HPC_MY_USAGE", 0) or 0)
    team_usage_value = float(env_data.get("HPC_TEAM_USAGE", 0) or 0)
    if capacity_value > 0:
        env_data["HPC_MY_PCT"] = round((my_usage_value / capacity_value) * 100, 2)
        env_data["HPC_TEAM_PCT"] = round((team_usage_value / capacity_value) * 100, 2)

    # Always write env file

    with open(OUTPUT_ENV_PATH, "w", encoding="ascii") as f:
        for key, value in env_data.items():
            f.write(f"{key}={value}\n")

    if VERBOSE:
        print()
        print(" HPC Usage Report ".center(60, "="))
        print()
        print(f"User: {user}")
        print(f"PI: {PI_NAME}")
        print(f"Partitions: {DEFAULT_PARTITION}")
        print()
        print(
            f"{'User usage':<25} {env_data["HPC_MY_USAGE"]:>15_} {env_data["HPC_MY_PCT"]:>17.2f}%".replace(
                "_", " "
            )
        )
        print(
            f"{'Team usage':<25} {env_data["HPC_TEAM_USAGE"]:>15_} {env_data["HPC_TEAM_PCT"]:>17.2f}%".replace(
                "_", " "
            )
        )
        print(
            f"{'Total budget':<25} {env_data["HPC_TEAM_BUDGET_YEAR"]:>15_} {100:>17.2f}%".replace(
                "_", " "
            )
        )
        print(
            f"{'(Total budget rep)':<25} {env_data["HPC_TEAM_BUDGET_YEAR_REPORTED"]:>15_} {100:>17.2f}%".replace(
                "_", " "
            )
        )
        print()
        print(" Budget per Cluster ".center(60, "-"))
        print()
        clusters_line = f"{'':<11}"
        budget_line = f"{'Budget':<11}"
        for cluster, value in env_data.get("HPC_TEAM_BUDGET_BY_CLUSTER", {}).items():
            clusters_line += f"{cluster:>13}"
            budget_line += f"{value:>13_}".replace("_", " ")

        print(clusters_line)
        print(budget_line)
        print()
        print(" Usage per User ".center(60, "-"))
        print()

        print(
            f"{'':<12}" + "".join(f"{cluster:>12}" for cluster in CLUSTERS + ["Total"])
        )

        users_info = env_data.get("HPC_USERS_INFO", {})

        # Sort users by total usage (descending)
        sorted_users = sorted(
            users_info.items(),
            key=lambda item: sum(item[1].get(c, 0) for c in CLUSTERS),
            reverse=True,
        )

        for user, usage_info in sorted_users:
            usage_line = f"{user:<12}"

            for cluster in CLUSTERS:
                used = usage_info.get(cluster, 0)
                usage_line += f"{used:>12_}".replace("_", " ")

            total = sum(usage_info.get(c, 0) for c in CLUSTERS)
            usage_line += f"{total:>12_}".replace("_", " ")

            print(usage_line)

        print()
        print("=" * 60)


if __name__ == "__main__":
    main()
