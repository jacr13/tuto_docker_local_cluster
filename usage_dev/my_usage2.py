#!/usr/bin/env python3
"""
Variant of my_usage that imports classes directly from the external scripts.
Paths are explicit so the scripts stay in their original locations on the cluster.
"""

import getpass
import importlib.util
import os
import sys
import types
from datetime import datetime, timedelta
from typing import List

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
UPDATE_INTERVALE = 1 # minutes

def load_module_from_path(name: str, path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Module path does not exist: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def ensure_pimanager_stub():
    if "pimanager" in sys.modules:
        return

    class _StubPIManager:
        def find_by_group(self, _):
            return []

    sys.modules["pimanager"] = types.SimpleNamespace(PIManager=_StubPIManager)

def get_year_capacity(Reporting):
    # Capacity per cluster
    total = 0
    info = {}
    for cluster in CLUSTERS:
        try:
            args = types.SimpleNamespace(
                nodes=None,
                partitions=[DEFAULT_PARTITION],
                cluster=cluster,
                summary=True,
                format="pretty",
                reference_year=datetime(REFERENCE_YEAR, 1, 1),
            )
            inventory_path = (
                f"/opt/cluster/inventory/simplified_inventory_{cluster}.yaml"
            )
            reporting = Reporting(args, inventory_path)
            reporting.read_yaml_inventory()
            reporting.subset_filter()
            summary = reporting._compute()
            cpuh = summary["cpuh_per_year"]
            total += int(cpuh)
            info[cluster] = int(cpuh)
        except Exception as exc:
            print(f"- {cluster}: failed to compute ({exc})")
    return total, info

def get_personal_usage(UsagePerAccount, UserPI, user, now):
    # Personal usage
    try:
        usage = UsagePerAccount()
        user_pi = UserPI()
        pi_names: List[str] = user_pi.get_pis_from_user(user, False)
        rows = []
        for pi_name in pi_names:
            data = usage.get_user_usage_by_account(
                user=user,
                cluster=None,
                pi_name=pi_name,
                start=YEAR_START,
                end=now,
                verbose=False,
                time_format="Hours",
                all_users=False,
                report_type="user",
            )
            if data:
                rows.extend(data)
        return sum(int(row["Used"]) for row in rows)
    except Exception as exc:
        print(f"\nPersonal usage lookup failed: {exc}")
    return 0

def get_team_usage(UsagePerAccount, user):
    # Team usage for PI kalousis
    try:
        usage = UsagePerAccount()
        rows = usage.get_user_usage_by_account(
            user=user,
            cluster=None,
            pi_name=PI_NAME,
            start=YEAR_START,
            end=YEAR_END,
            verbose=False,
            time_format="Hours",
            all_users=True,
            report_type="user",
        )
        return sum(int(row["Used"]) for row in rows) if rows else 0

    except Exception as exc:
        print(f"Team usage lookup failed: {exc}")
    return 0

def main():
    ensure_pimanager_stub()

    # Make sure slurmpartitions import resolves before loading node summary.
    if "slurmpartitions" not in sys.modules and os.path.exists(SLURMPARTITIONS_PATH):
        load_module_from_path("slurmpartitions", SLURMPARTITIONS_PATH)

    usage_mod = load_module_from_path("ug_slurm_usage_per_user", UG_SLURM_USAGE_PATH)
    node_mod = load_module_from_path(
        "ug_getNodeCharacteristicsSummary", UG_NODE_SUMMARY_PATH
    )

    Reporting = node_mod.Reporting  # type: ignore[attr-defined]
    UsagePerAccount = usage_mod.UsagePerAccount  # type: ignore[attr-defined]
    UserPI = usage_mod.UserPI  # type: ignore[attr-defined]

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
        capacity_total, capacity_info = get_year_capacity(Reporting)
        env_data = {
                "HPC_MY_USAGE": get_personal_usage(UsagePerAccount, UserPI, user, now),
                "HPC_TOTAL_USAGE": get_team_usage(UsagePerAccount, user),
                "HPC_CAPACITY_YEAR": capacity_total,
                "HPC_CAPACITY_INFO": capacity_info,
                "HPC_MY_PCT": 0,
                "HPC_MAX_PCT": 100 // DMML_HPC_USERS,
                "LAST_HPC_USAGE_UPDATE": now,
            }

    # Compute percentages
    capacity_value = float(env_data.get("HPC_CAPACITY_YEAR", 1) or 1)
    my_usage_value = float(env_data.get("HPC_MY_USAGE", 0) or 0)
    if capacity_value > 0:
        env_data["HPC_MY_PCT"] = round((my_usage_value / capacity_value) * 100, 2)

    # Always write env file
 
    with open(OUTPUT_ENV_PATH, "w", encoding="ascii") as f:
        for key, value in env_data.items():
            f.write(f"{key}={value}\n")

    if VERBOSE:
        print(env_data)


if __name__ == "__main__":
    main()
