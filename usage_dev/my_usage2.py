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
from datetime import datetime
from typing import List

UG_SLURM_USAGE_PATH = "/usr/local/bin/ug_slurm_usage_per_user.py"
UG_NODE_SUMMARY_PATH = "/usr/local/sbin/ug_getNodeCharacteristicsSummary.py"
SLURMPARTITIONS_PATH = "/usr/local/sbin/slurmpartitions.py"

REFERENCE_YEAR = datetime.today().year
YEAR_START = f"{REFERENCE_YEAR}-01-01"
YEAR_END = f"{REFERENCE_YEAR+1}-01-01"

DEFAULT_PARTITION = "private-kalousis-gpu"
CLUSTERS = ["baobab", "yggdrasil", "bamboo"]


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
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    total_hours = 0
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
            total_hours += cpuh
        except Exception as exc:
            print(f"- {cluster}: failed to compute ({exc})")

    print(
        f"Cluster total CPU hours in {REFERENCE_YEAR} "
        f"for partition '{DEFAULT_PARTITION}': "
        f"{total_hours} hours"
    )

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
        total_hours = sum(int(row["Used"]) for row in rows)
        print(
            f"\nPersonal usage since {YEAR_START} (accounts: {', '.join(pi_names)}): "
            f"{total_hours} hours"
        )
    except Exception as exc:
        print(f"\nPersonal usage lookup failed: {exc}")

    # Team usage for PI kalousis
    try:
        usage = UsagePerAccount()
        rows = usage.get_user_usage_by_account(
            user=user,
            cluster=None,
            pi_name="kalousis",
            start=YEAR_START,
            end=YEAR_END,
            verbose=False,
            time_format="Hours",
            all_users=True,
            report_type="user",
        )
        total_hours = sum(int(row["Used"]) for row in rows) if rows else 0
        print(
            f"Team usage for PI 'kalousis' ({YEAR_START} to {YEAR_END}): "
            f"{total_hours} hours"
        )
    except Exception as exc:
        print(f"Team usage lookup failed: {exc}")


if __name__ == "__main__":
    main()
