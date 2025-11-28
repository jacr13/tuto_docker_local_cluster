import re
import subprocess
from typing import List

from ClusterShell.NodeSet import NodeSet


class SlurmPartition:
    def __init__(self, cluster, *partitions: str):
        self._partitions = partitions
        self._cluster = cluster

    def run_sinfo(self) -> str:
        try:
            result = subprocess.run(
                [
                    "sinfo",
                    "-h",
                    "--clusters",
                    self._cluster,
                    "-p",
                    ",".join(self._partitions),
                    "-o",
                    "%N",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'exécution de sinfo: {e}")
            return ""

    def get_nodes(self) -> NodeSet:
        return NodeSet(self.run_sinfo())


def main():
    partition = SlurmPartition("baobab", "shared-gpu", "shared-cpu")
    print(partition.get_nodes())


if __name__ == "__main__":
    main()
