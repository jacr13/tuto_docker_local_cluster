#!/usr/bin/env python3
"""
Utility script that reuses the cluster helper scripts to report:
- cpuh_per_year capacity per cluster (from ug_getNodeCharacteristicsSummary.py)
- personal usage since the start of the current year
- total team usage for PI "kalousis" for the current year

Both external scripts are loaded from the absolute paths defined below so they
can stay in their original locations on the cluster.
"""

import getpass
import importlib.util
import os
import sys
import types
from datetime import datetime
from typing import Dict, List

UG_SLURM_USAGE_PATH = "/usr/local/bin/ug_slurm_usage_per_user.py"
UG_NODE_SUMMARY_PATH = "/usr/local/sbin/ug_getNodeCharacteristicsSummary.py"
YEAR_START = "2025-01-01"
YEAR_END = "2026-01-01"
REFERENCE_YEAR = datetime.fromisoformat(YEAR_START).year
DEFAULT_PARTITION = "private-kalousis-gpu"
_SLURMPARTITIONS_AVAILABLE = False


def load_external_module(name: str, path: str):
    """Load a Python script by absolute path as a module."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Module path does not exist: {path}")

    def _load():
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {name} from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[attr-defined]
        return module

    try:
        return _load()
    except ModuleNotFoundError as exc:
        # If slurmpartitions is missing, inject stub and retry once.
        if exc.name == "slurmpartitions":
            ensure_slurmpartitions_stub()
            return _load()
        raise


def ensure_pimanager_stub():
    """
    Provide a lightweight stub for pimanager if it is not installed.
    The stub satisfies the import in ug_slurm_usage_per_user, which only needs
    PIManager when the --group CLI option is used (not used here).
    """
    if "pimanager" in sys.modules:
        return

    class _StubPIManager:
        def find_by_group(self, _):
            return []

    stub_mod = types.SimpleNamespace(PIManager=_StubPIManager)
    sys.modules["pimanager"] = stub_mod


def ensure_slurmpartitions_stub():
    """
    Provide a lightweight stub for slurmpartitions.SlurmPartition if missing.
    Only used when CLI passes --partitions in the original script; our usage
    path bypasses that, so the stub can be minimal.
    """
    if "slurmpartitions" in sys.modules:
        return

    class _StubSlurmPartition:
        def __init__(self, *_args, **_kwargs):
            pass

        def get_nodes(self):
            return []

    stub_mod = types.SimpleNamespace(SlurmPartition=_StubSlurmPartition)
    sys.modules["slurmpartitions"] = stub_mod
    globals()["_SLURMPARTITIONS_AVAILABLE"] = False


def compute_cpuh_per_year(
    node_summary_module, cluster: str, partition: str | None, reference_year: int
):
    """
    Compute cpuh_per_year using the Reporting class without invoking argparse,
    optionally filtering by a partition list. If slurmpartitions is missing,
    fall back to manual inventory filtering.
    """
    inventory_path = f"/opt/cluster/inventory/simplified_inventory_{cluster}.yaml"

    # If slurmpartitions is present, use the full Reporting workflow.
    if _SLURMPARTITIONS_AVAILABLE:
        args = types.SimpleNamespace(
            nodes=None,
            partitions=[partition] if partition else None,
            cluster=cluster,
            summary=True,
            format="pretty",
            reference_year=datetime(reference_year, 1, 1),
        )
        reporting = node_summary_module.Reporting(args, inventory_path)
        reporting.read_yaml_inventory()
        reporting.subset_filter()
        summary = reporting._compute()
        return summary["cpuh_per_year"]

    # Fallback: manual computation with basic partition filtering from inventory.
    yaml = node_summary_module.yaml
    relativedelta = node_summary_module.relativedelta

    with open(inventory_path, "r") as file:
        inventory = yaml.safe_load(file)

    ref_year_dt = datetime(reference_year, 1, 1)
    usage_ratio = 0.6
    max_year_in_production = 5
    hours_per_year = 24 * 365

    def start_production(node: dict):
        if "leasing" in node and "start_date" in node["leasing"]:
            return datetime.strptime(node["leasing"]["start_date"], "%Y-%m-%d")
        return datetime.strptime(node["purchasedate"], "%Y-%m-%d")

    def end_production(node: dict):
        if "leasing" in node and "end_date" in node["leasing"]:
            return datetime.strptime(node["leasing"]["end_date"], "%Y-%m-%d")
        extended_months = node.get("extended_prod_in_months", 0)
        return datetime.strptime(node["purchasedate"], "%Y-%m-%d") + relativedelta(
            years=max_year_in_production, months=extended_months
        )

    def months_in_production_this_year(node: dict) -> int:
        start_of_year = datetime(ref_year_dt.year, 1, 1)
        end_of_year = datetime(ref_year_dt.year, 12, 31)

        start_date = start_production(node)
        end_date = end_production(node)
        if end_date < start_of_year:
            return 0

        prod_start = max(start_date, start_of_year)
        prod_end = min(end_date, end_of_year)
        if prod_end < prod_start:
            return 0

        delta = relativedelta(prod_end, prod_start)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

    def partition_matches(node: dict, target: str | None) -> bool:
        if target is None:
            return True
        # Try common keys in the inventory for partition membership.
        parts = node.get("partitions") or node.get("partition")
        if parts is None:
            return False
        if isinstance(parts, str):
            parts_list = [p.strip() for p in parts.split(",")]
        else:
            parts_list = [str(p) for p in parts]
        return target in parts_list

    total_billing = 0
    for node in inventory.values():
        if not partition_matches(node, partition):
            continue
        months = months_in_production_this_year(node)
        billing_per_year = months * int(node["billing"]) / 12
        total_billing += billing_per_year

    return hours_per_year * total_billing * usage_ratio


def gather_usage(
    usage_module,
    user: str,
    start: str,
    end: str,
    pi: str | None = None,
    all_users: bool = False,
    report_type: str = "user",
) -> Dict:
    """
    Run the logic from ug_slurm_usage_per_user to collect usage rows and totals.
    """
    usage = usage_module.UsagePerAccount()
    user_pi = usage_module.UserPI()

    pi_names: List[str] = [pi] if pi else user_pi.get_pis_from_user(user, False)
    if not pi_names:
        raise RuntimeError(f"No PI found for user '{user}'.")

    rows = []
    for pi_name in pi_names:
        data = usage.get_user_usage_by_account(
            user=user,
            cluster=None,
            pi_name=pi_name,
            start=start,
            end=end,
            verbose=False,
            time_format="Hours",
            all_users=all_users,
            report_type=report_type,
        )
        if data:
            rows.extend(data)

    total_hours = sum(int(row["Used"]) for row in rows)
    total_formatted = usage_module.StringUtils().format_millions(total_hours)

    return {
        "rows": rows,
        "pi_names": pi_names,
        "total_hours": total_hours,
        "total_formatted": total_formatted,
    }


def main():
    global _SLURMPARTITIONS_AVAILABLE
    try:
        import slurmpartitions as _sp  # type: ignore
        _SLURMPARTITIONS_AVAILABLE = True
    except ModuleNotFoundError:
        ensure_slurmpartitions_stub()
        _SLURMPARTITIONS_AVAILABLE = False

    try:
        ensure_pimanager_stub()
        usage_module = load_external_module(
            "ug_slurm_usage_per_user", UG_SLURM_USAGE_PATH
        )
        node_summary_module = load_external_module(
            "ug_getNodeCharacteristicsSummary", UG_NODE_SUMMARY_PATH
        )
    except Exception as exc:
        print(f"Failed to load external modules: {exc}")
        sys.exit(1)

    user = getpass.getuser()
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    clusters = ["baobab", "yggdrasil", "bamboo"]
    print("Cluster cpuh_per_year capacity")
    for cluster in clusters:
        try:
            cpuh_per_year = compute_cpuh_per_year(
                node_summary_module,
                cluster,
                partition=DEFAULT_PARTITION,
                reference_year=REFERENCE_YEAR,
            )
            print(
                f"- {cluster}: {cpuh_per_year / 1_000_000:.2f}M CPUh/year "
                f"({int(cpuh_per_year)} raw)"
            )
        except Exception as exc:
            print(f"- {cluster}: failed to compute ({exc})")

    # Personal usage (current year)
    try:
        personal_usage = gather_usage(
            usage_module=usage_module,
            user=user,
            start=YEAR_START,
            end=now,
            all_users=False,
            report_type="user",
        )
        print(
            f"\nPersonal usage since {YEAR_START} "
            f"(accounts: {', '.join(personal_usage['pi_names'])}): "
            f"{personal_usage['total_formatted']} hours"
        )
    except Exception as exc:
        print(f"\nPersonal usage lookup failed: {exc}")

    # Team usage for PI kalousis (current year window)
    try:
        team_usage = gather_usage(
            usage_module=usage_module,
            user=user,
            start=YEAR_START,
            end=YEAR_END,
            pi="kalousis",
            all_users=True,
            report_type="user",
        )
        print(
            f"Team usage for PI 'kalousis' ({YEAR_START} to {YEAR_END}): "
            f"{team_usage['total_formatted']} hours"
        )
    except Exception as exc:
        print(f"Team usage lookup failed: {exc}")


if __name__ == "__main__":
    main()
