#!/bin/env python3

import argparse
import sys
from datetime import datetime

from dateutil.relativedelta import relativedelta


class ArgumentParser:
    """
    Classe pour gérer le parsing des arguments du script.
    """

    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Retrieve HPC utilization statistics for a user or group of users."
        )
        self._configure_arguments()

    def _configure_arguments(self):
        first_day_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%dT00:00:00")
        current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        self.parser.add_argument("--user", help="Username to retrieve usage for.")
        self.parser.add_argument(
            "--start",
            default=first_day_of_month,
            help="Start date (default: first of month).",
        )
        self.parser.add_argument(
            "--end", default=current_time, help="End date (default: now)."
        )
        self.parser.add_argument("--pi", help="Specify a PI manually.")
        self.parser.add_argument(
            "--group", help="Specify a group name to get all PIs belonging to it."
        )
        self.parser.add_argument(
            "--cluster",
            choices=["baobab", "yggdrasil", "bamboo"],
            help="Cluster name (default: all clusters).",
        )
        self.parser.add_argument(
            "--all-users",
            action="store_true",
            help="Include all users under the PI account.",
        )
        self.parser.add_argument(
            "--aggregate", action="store_true", help="Aggregate the usage per user."
        )
        self.parser.add_argument(
            "--report-type",
            choices=["user", "account"],
            default="user",
            help="Type of report: user (default) or account.",
        )
        self.parser.add_argument(
            "--time-format",
            choices=["Hours", "Minutes", "Seconds"],
            default="Hours",
            help="Time format: Hours (default), Minutes, or Seconds.",
        )
        self.parser.add_argument(
            "--verbose", action="store_true", help="Verbose output."
        )
        self.parser.add_argument(
            "--invoice", action="store_true", help=argparse.SUPPRESS
        )
        self.parser.add_argument("--pi-gecos", help=argparse.SUPPRESS)
        self.parser.add_argument("--pi-email", help=argparse.SUPPRESS)
        self.parser.add_argument(
            "--send-email", action="store_true", help=argparse.SUPPRESS
        )
        self.parser.add_argument(
            "--csv-output", action="store_true", help=argparse.SUPPRESS
        )
        self.parser.add_argument(
            "--pdf-output", action="store_true", help=argparse.SUPPRESS
        )

    def parse(self, extra=None):
        """
        Parse les arguments et retourne l'objet Namespace.
        """
        return self.parser.parse_args(extra)
