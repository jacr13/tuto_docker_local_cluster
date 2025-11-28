#!/usr/bin/env python3

try:
    import argparse
    import csv
    import getpass
    import subprocess
    import sys
    from datetime import datetime
    from io import StringIO

    from tabulate2 import tabulate
except ModuleNotFoundError as e:
    print(f"Missing module {e}")
    print(
        "Please load the needed modules. Ex: module load GCCcore/13.3.0 Python/3.12.3 tabulate2/1.10.0 PyYAML/6.0.2"
    )
    exit(1)

if sys.version_info <= (3, 8):
    print(
        "Python 3.8 or newer mandatory. You can use module to use a different python version: ml GCCcore/13.3.0 Python/3.12.3  tabulate2/1.10.0 PyYAML/6.0.2"
    )
    print(f"Current version : {sys.version}")
    sys.exit(1)

from pimanager import PIManager


class UserPI:
    def __init__(self):
        self.user = ""

    def get_pis_from_user(self, user, verbose):
        """
        Retrieves the DefaultAccount and Account information for a specific user using sacctmgr.

        Parameters:
            user (str): The username to query.

        Returns:
            list: The DefaultAccount (PI name) for the user and optionnal ExtraAccount(s). First account is the default
                 Returns empty list if no DefaultAccount is found.
        """
        # Command to execute
        command = [
            "sacctmgr",
            "show",
            "User",
            f"user={user}",
            "-s",
            "Format=user,DefaultAccount,Account",
            "cluster=Baobab",
            "--parsable2",
        ]

        try:
            # Run the command and capture the output
            # print("Executing command:", " ".join(command))
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            result = []
            # Parse the CSV output
            csv_reader = csv.DictReader(StringIO(output), delimiter="|")
            for row in csv_reader:
                if row["Def Acct"] not in result:
                    result.append(row["Def Acct"])
                if row["Account"] not in result:
                    result.append(row["Account"])
            return result
        except subprocess.CalledProcessError as e:
            print(f"Error running sacctmgr: {e}")
            print(f"stderr: {e.stderr}")
            return None
        except FileNotFoundError:
            print("sacctmgr not found.")
            return None


class Report:
    def __init__(self, cluster, login, proper, account, tresname, used):
        self.report = []
        self.cluster = cluster
        self.login = login
        self.proper = proper
        self.account = account
        self.tresname = tresname
        self.used = used

    def __repr__(self):
        report["cluster"] = self.cluster
        cluster["login"] = self.login
        cluster["proper"] = self.proper
        cluster["account"] = self.account
        cluster["tresname"] = self.tresname
        return cluster


class StringUtils:
    def format_millions(self, value):
        return f"{value / 1_000_000:.2f}M"


class UsagePerAccount:
    def __init__(self):
        self.output = ""
        self.header = ""

    def getHeader(self):
        return self.header

    def parseSreport(self):
        f = StringIO(self.output)
        lines = f.readlines()

        # first 4 lines are header. We store them for future use
        self.header = lines[0:4]

        # we skip the first four lines
        csv_reader = csv.DictReader(lines[4:], delimiter="|")
        return list(csv_reader)

    def get_user_usage_by_account(
        self,
        user,
        cluster,
        pi_name,
        start,
        end,
        verbose,
        time_format,
        all_users,
        report_type,
    ):
        sreport_format = "Cluster,Login%15,Proper%20,Account,TresName,Used"

        sreport_tres = "ALL" if verbose else "billing"
        sreport_clusters = f"--cluster={cluster}" if cluster else "--all_clusters"
        sreport_users = f"users={user}" if not all_users else None

        # Command to execute
        # We have two reports available:
        # 1. "AccountUtilizationByUser"
        # 2. "UserUtilizationByAccount" : you see the user utilization

        cmd = []
        cmd.append("sreport")
        cmd.append(f"{sreport_clusters}")
        cmd.append("-t")
        cmd.append(f"{time_format}")
        cmd.append(f"--parsable2")
        cmd.append(f"--tres={sreport_tres}")
        cmd.append("Cluster")
        if report_type == "user":
            cmd.append("UserUtilizationByAccount")
            if sreport_users:
                cmd.append(sreport_users)
        else:
            cmd.append("AccountUtilizationByUser")
            if not all_users:
                cmd.append("User=")
        cmd.append(f"Accounts={pi_name}")
        cmd.append(f"start={start}")
        cmd.append(f"end={end}")
        cmd.append(f"Format={sreport_format}")

        try:
            if verbose:
                print("Executing command:", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.output = result.stdout
            return self.parseSreport()
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            print(f"stderr: {e.stderr}")


def parseArgs(first_day_of_month, current_time):
    parser = argparse.ArgumentParser(
        description="Retrieve HPC utilization statistics for a user or group of users."
    )
    parser.add_argument("--user", help="Username to retrieve usage for.")
    parser.add_argument(
        "--start",
        default=first_day_of_month,
        help="Start date (default: first of month).",
    )
    parser.add_argument("--end", default=current_time, help="End date (default: now).")
    parser.add_argument("--pi", help="Specify a PI manually.")
    parser.add_argument(
        "--group", help="Specify a group name to get all PIs belonging to it."
    )
    parser.add_argument(
        "--cluster",
        choices=["baobab", "yggdrasil", "bamboo"],
        help="Cluster name (default: all clusters).",
    )
    parser.add_argument(
        "--all_users",
        action="store_true",
        help="Include all users under the PI account.",
    )
    parser.add_argument(
        "--report_type",
        choices=["user", "account"],
        default="user",
        help="Type of report: user (default) or account.",
    )
    parser.add_argument(
        "--time_format",
        choices=["Hours", "Minutes", "Seconds"],
        default="Hours",
        help="Time format: Hours (default), Minutes, or Seconds.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output.")
    return parser.parse_args()


def main():
    # Default to the first day of the current month if no start date is provided
    first_day_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%dT00:00:00")
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    args = parseArgs(first_day_of_month, current_time)

    user = args.user or getpass.getuser()
    if not user or user == "root":
        print("Error: could not determine user or running as root.")
        return

    string_utils = StringUtils()

    userpi = UserPI()
    clusters = args.cluster

    # Détermination des PI à utiliser
    if args.group:
        manager = PIManager()
        pis_from_group = manager.find_by_group(args.group)
        if not pis_from_group:
            print(f"No PIs found in group '{args.group}'.")
            return
        pi_names = [pi.name for pi in pis_from_group]
        if args.verbose:
            print(f"PIs in group '{args.group}': {', '.join(pi_names)}")
    elif args.pi:
        pi_names = [args.pi]
    else:
        pi_names = userpi.get_pis_from_user(user, args.verbose)
        if not pi_names:
            print(f"Error: No PI found for user '{user}'. Use --pi or --group.")
            return

    usage = UsagePerAccount()

    res = []
    for pi_name in pi_names:
        usage_by_account = usage.get_user_usage_by_account(
            user,
            clusters,
            pi_name,
            args.start,
            args.end,
            args.verbose,
            args.time_format,
            args.all_users,
            args.report_type,
        )
        for i in usage_by_account:
            res.append(i)

    # print header (multiline)
    for i in usage.getHeader():
        print(i)
    # print cluster usage
    print(tabulate(res, headers="keys"))

    if not args.verbose:
        total_usage = 0
        for i in res:
            total_usage += int(i["Used"])
        print(f"Total usage: {string_utils.format_millions(total_usage)}")


if __name__ == "__main__":
    main()
