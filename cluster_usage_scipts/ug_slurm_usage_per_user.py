#!/usr/bin/env python3

try:
    import argparse
    import csv
    import getpass
    import subprocess
    import sys
    from collections import defaultdict
    from datetime import datetime
    from io import StringIO
    from pathlib import Path

    from tabulate2 import tabulate
    from ug_slurm_parse_args import ArgumentParser
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


class StringUtils:
    def format_millions(self, value):
        return f"{value / 1_000_000:.2f}M"


class UsagePerAccount:
    def __init__(self):
        self.output = ""
        self.header = ""

    def getHeader(self):
        return self.header

    def parseSreport(self, all_users, aggregate):
        f = StringIO(self.output)
        lines = f.readlines()

        # first 4 lines are header. We store them for future use
        self.header = lines[0:4]

        # cleanup empty lines and skip header
        data_lines = [line.strip() for line in lines[4:] if line.strip()]

        # we parse the data
        csv_reader = csv.DictReader(data_lines, delimiter="|")

        # if we display all users we skip account only line (PI)
        if all_users:
            # On ne garde que les lignes où 'Login' est renseigné (→ utilisateurs)
            rows = [row for row in csv_reader if row.get("Login", "").strip() != ""]
            if aggregate:
                rows = self.aggregate_by_user(rows)
        else:
            # On renvoie tout tel quel
            rows = list(csv_reader)
        return rows

    def _to_float(self, x: str) -> float:
        """Convertit 'Used' en float (gère espaces, virgules, milliers)."""
        if not x:
            return 0.0
        s = str(x).strip().replace("\u00a0", " ").replace(" ", "")
        if s == "":
            return 0.0
        if "," in s and "." in s:
            s = s.replace(",", "")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return 0.0

    def aggregate_by_user(self, reader):
        """
        Agrège la consommation 'billing' par utilisateur (Login),
        """
        totals = defaultdict(float)
        for row in reader:
            login = (row.get("Login") or "").strip()
            if not login:  # ignore ligne agrégat account
                continue
            used = self._to_float(row.get("Used", "0"))
            totals[login] += used

        result = [{"Login": u, "Used": round(v, 2)} for u, v in totals.items()]
        result.sort(key=lambda x: x["Used"], reverse=True)
        return result

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
        aggregate,
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
            return self.parseSreport(all_users, aggregate)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            print(f"stderr: {e.stderr}")


def printDetailedUsage(usage, res, verbose):
    string_utils = StringUtils()

    # print header (multiline)
    for i in usage.getHeader():
        print(i)
    # print cluster usage
    print(tabulate(res, headers="keys"))

    if not verbose:
        total_usage = 0
        for i in res:
            total_usage += int(i["Used"])
        print(f"Total usage: {string_utils.format_millions(total_usage)}")


def getSumUsage(res):
    total_usage = 0
    for i in res:
        total_usage += int(i["Used"])
    return total_usage


def main():
    # Default to the first day of the current month if no start date is provided
    args = ArgumentParser().parse()

    user = args.user or getpass.getuser()
    if not user or user == "root" and args.report_type != "account":
        print("Error: could not determine user or running as root.")
        return

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
            user=user,
            cluster=clusters,
            pi_name=pi_name,
            start=args.start,
            end=args.end,
            verbose=args.verbose,
            time_format=args.time_format,
            all_users=args.all_users,
            report_type=args.report_type,
            aggregate=args.aggregate,
        )
        for i in usage_by_account:
            res.append(i)

    if args.invoice:
        from hpc_invoice import HPCInvoice

        invoice = HPCInvoice()
        result = invoice.process(
            pi_name=pi_name,
            pi_gecos=args.pi_gecos,
            pi_email=args.pi_email,
            start_date=args.start,
            res=res,
            get_sum_usage=getSumUsage,
            invoice_seq="001",
            csv_output=bool(args.csv_output),
            pdf_output=bool(args.pdf_output),
        )

        if args.csv_output and "csv_line" in result:
            print(result["csv_line"])

        if result["status"] == "skip_invoice":
            print(f"No hours consumed this year, skipping invoice for {pi_name}")

        if args.pdf_output and "pdf_path" in result:
            print(f"PDF generated: {result['pdf_path']}")

        # result_html= md_to_email.convert_markdown_to_html(result_md)

        if args.send_email:
            # md_to_email.send_email(result_md, f"[HPC] Baobab invoice {invoice_ref} 2025", mail_from, mail_to, mail_cc)
            print(f"Email sent to {mail_to}")
            return
        # else:
        #  print(result_html)
        #  return

    else:
        printDetailedUsage(usage, res, args.verbose)


if __name__ == "__main__":
    main()
