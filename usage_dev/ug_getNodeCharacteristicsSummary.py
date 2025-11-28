#!/bin/env python3
##
## This script reads the compute node inventory of a given nodeset and output it in CSV or formated table
## It prints also the summary of the nodes characteristics such as total amount of cpus, gpus, memory etc.
## Yann Sagon <yann.sagon@unige.ch>
## 2024-12
##


try:
    import argparse
    import csv
    import importlib.util
    import sys
    from datetime import datetime

    import yaml
    from ClusterShell.NodeSet import NodeSet
    from dateutil.relativedelta import relativedelta
    from slurmpartitions import SlurmPartition
    from tabulate import tabulate
except ModuleNotFoundError as e:
    print(f"Missing module {e}")
    print(
        "Please load tabulate and ClusterShell module. Ex: module load GCCcore/13.3.0 ClusterShell/1.9.3 tabulate2/1.10.0"
    )
    exit(1)


def module_available(module_name):
    return importlib.util.find_spec(module_name) is not None


def import_module(module):
    module = importlib.import_module(module)
    return module


def parseArgs():
    parser = argparse.ArgumentParser(
        description="Script to read the compute node inventory of a given nodeset and output summary as CSV"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-n", "--nodes", help="Specify the nodeset to lookup")
    group.add_argument(
        "-p", "--partitions", nargs="+", help="Specify the partitions to lookup"
    )
    parser.add_argument(
        "-c",
        "--cluster",
        choices=["baobab", "yggdrasil", "bamboo"],
        help="Specify on which cluster to lookup for the compute nodes",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--summary",
        help="Print the summary line in addition to the resource list",
        action="store_true",
    )
    parser.add_argument(
        "--reference-year",
        type=lambda s: datetime.strptime(s, "%Y"),
        default=datetime(datetime.today().year, 1, 1),
        help="""Reference year in YYYY format used to calculate the remaining months that the node will remain available in private partition. 
          The number of year a node is available is 5 yeaar. (default: today's date)""",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "pretty", "html"],  # Limite aux choix possibles
        default="pretty",
        required=False,  # Optionnel
        help="Output format : 'csv', 'html', 'pretty' (default)",
    )
    return parser.parse_args()


class Reporting:
    def __init__(self, args, inventory_path):
        """
        Initializes the class with the nodeset to query.
        :param nodeset: Name of the node group to retrieve.
        """
        if args.partitions:
            sinfo = SlurmPartition(args.cluster, *args.partitions)
            self._nodes = sinfo.get_nodes()
        else:
            self._nodes = NodeSet(args.nodes)
        self._partitions = args.partitions
        self._cluster = args.cluster
        self._reference_year = args.reference_year
        self._usage_ratio = 0.6
        self._max_year_in_production = 5
        self._hours_per_year = 24 * 365
        self._inventory_path = inventory_path
        self._inventory = None
        self._subset = None
        self._nodes_parsed = []

    def read_yaml_inventory(self):
        # Read the yaml inventory file
        with open(self._inventory_path, "r") as file:
            inventory = yaml.safe_load(file)
        self._inventory = inventory

    def get_header(self):
        return [
            "host",
            "sn",
            "cpu",
            "mem",
            "gpunumber",
            "gpudeleted",
            "gpumodel",
            "gpumemory",
            "purchasedate",
            f"months in prod this year",
            f"months remaining in prod. (Jan {self._reference_year.year})",
            "billing",
        ]

    def csv_output(self):
        self._nodes_parsed.insert(0, self.get_header())
        # Write the output in stdout
        writer = csv.writer(sys.stdout)
        writer.writerows(self._nodes_parsed)

    def html_print(self):
        data = self._nodes_parsed
        print(tabulate(data, headers=self.get_header(), tablefmt="html"))

    def pretty_print(self):
        data = self._nodes_parsed
        print(tabulate(data, headers=self.get_header()))

    def get_summary(self):
        summary = self._compute()
        output = (
            f"Total CPUs: {summary['cpu']} "
            f"Total CPUs memory[GB]: {summary['mem']} "
            f"Total GPUs: {summary['gpu']} "
            f"Total GPUs memory[MB]: {summary['gpumemory']} "
            f"Billing: {int(summary['billing'])} "
            f"CPUhours per year: {self._format_millions(summary['cpuh_per_year'])}"
        )
        length = int(len(output) / 2)
        return "=" * (length - 4) + " Summary " + "=" * (length - 4) + "\n" + output

    def subset_filter(self):
        filter_nodes = self._nodes
        self._subset = {
            key: self._inventory[key] for key in filter_nodes if key in self._inventory
        }
        return self._subset

    def _compute(self):
        """sum the number of cpu, gpu, memory, billing of each nodes from self._subset
        return a dict with cpu,gpu,gpumemory,billing,cpuh_per_year
        """
        subset = self._subset
        sum = {}
        sum["cpu"] = 0
        sum["gpu"] = 0
        sum["mem"] = 0
        sum["gpumemory"] = 0
        sum["billing"] = 0
        for node in subset:
            sum["cpu"] += subset[node]["cpu"]
            sum["gpu"] += subset[node]["gpunumber"] - subset[node]["gpudeleted"]
            sum["mem"] += subset[node]["mem"]
            sum["gpumemory"] += int(float(subset[node]["gpumemory"]))
            # number of billing per year per node depending on the months in production
            sum["billing"] += self._billing_per_year_per_node(node)
            # sum['billing'] += int(subset[node]['billing'])
        sum["cpuh_per_year"] = self._compute_hours_per_year(sum["billing"])
        return sum

    def _define_start_production_date(self, node: dict):
        # 1) Définir la date de mise en production
        if "leasing" in node and "start_date" in node["leasing"]:
            start_date = datetime.strptime(node["leasing"]["start_date"], "%Y-%m-%d")
        else:
            start_date = datetime.strptime(node["purchasedate"], "%Y-%m-%d")
        return start_date

    def _define_end_production_date(self, node: dict):
        # 2) Définir la date de fin de mise en production
        if "leasing" in node and "end_date" in node["leasing"]:
            end_date = datetime.strptime(node["leasing"]["end_date"], "%Y-%m-%d")
        else:
            extended_months = node.get("extended_prod_in_months", 0)
            end_date = datetime.strptime(
                node["purchasedate"], "%Y-%m-%d"
            ) + relativedelta(
                years=self._max_year_in_production, months=extended_months
            )
        return end_date

    def _months_in_production_this_year(
        self, node: dict, reference_year: int = None
    ) -> int:
        """
        Calcule le nombre de mois en production pour un nœud durant l'année donnée.

        :param node: Dictionnaire contenant les infos du nœud (purchase_date, leasing.start, leasing.end, etc.)
        :param reference_year: Année de référence (par défaut, l'année actuelle)
        :return: Nombre de mois en production durant l'année
        """
        today = datetime.today()
        year = reference_year or today
        start_of_year = datetime(year.year, 1, 1)
        end_of_year = datetime(year.year, 12, 31)

        start_date = self._define_start_production_date(node)

        end_date = self._define_end_production_date(node)

        # Si le nœud est déjà hors production
        if end_date < start_of_year:
            return 0
        # Calculer la période de production dans l'année
        prod_start = max(start_date, start_of_year)
        prod_end = min(end_date, end_of_year)

        if prod_end < prod_start:
            return 0

        delta = relativedelta(prod_end, prod_start)
        return delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)

    def _billing_per_year_per_node(self, node):
        # number of months remaining in specified year (0..12)
        number_of_months = self._months_in_production_this_year(
            self._subset[node], self._reference_year
        )
        # billing prorata
        return number_of_months * int(self._subset[node]["billing"]) / 12

    def _compute_hours_per_year(self, billing):
        return self._hours_per_year * billing * self._usage_ratio

    def _format_millions(self, value):
        return f"{value / 1_000_000:.2f}M"

    def _remaining_months_in_production(self, node):
        start_date = self._define_start_production_date(node)
        end_date = self._define_end_production_date(node)

        # purchase_date_obj = datetime.strptime(node['purchasedate'], "%Y-%m-%d")
        # expiration_date = purchase_date_obj + relativedelta(years=self._max_year_in_production)
        # expiration_date = end_date + relativedelta(years=self._max_year_in_production)

        # delta = relativedelta(expiration_date, self._reference_year)
        delta = relativedelta(end_date, self._reference_year)
        remaining_months = delta.years * 12 + delta.months
        return max(remaining_months, 0)

    def parse_nodes(self):
        self._nodes_parsed = []
        for node in self._subset:
            idx = self._subset[node]
            self._nodes_parsed.append(
                [
                    node,
                    idx["sn"],
                    idx["cpu"],
                    idx["mem"],
                    idx["gpunumber"],
                    idx["gpudeleted"],
                    idx["gpumodel"],
                    idx["gpumemory"],
                    idx["purchasedate"],
                    self._months_in_production_this_year(idx, self._reference_year),
                    self._remaining_months_in_production(idx),
                    idx["billing"],
                ]
            )


def main():
    if sys.version_info <= (3, 8):
        print(
            f"Python version is too old: please load Python and needed modules. Ex: module load GCCcore/13.3.0 ClusterShell/1.9.3 tabulate2/1.10.0"
        )
        exit()

    args = parseArgs()

    # nodes = NodeSet(args.nodes)

    inventory_file_path = (
        f"/opt/cluster/inventory/simplified_inventory_{args.cluster}.yaml"
    )

    reporting = Reporting(args, inventory_file_path)

    reporting.read_yaml_inventory()

    reporting.subset_filter()

    reporting.parse_nodes()

    if args.format == "csv":
        reporting.csv_output()
    # else:
    # if tabulate:
    elif args.format == "pretty":
        reporting.pretty_print()
    else:
        reporting.html_print()
    if args.summary:
        print("")
        print(reporting.get_summary())


if __name__ == "__main__":
    main()
