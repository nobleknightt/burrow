"""burrow dig - you found it."""

import argparse
import time

POEM = """
    The Burrow

    No front door, no welcome mat,
    no VPN, no this-or-that.
    Just a key, a host, a port,
    and a tunnel of the underground sort.

    The mole does not knock.
    The mole does not ask.
    The mole picks a port,
    and gets on with the task.

    Through bastion it goes,
    where the firewall sleeps,
    and surfaces quietly
    where the database keeps

    its tables, its indexes,
    its rows in the dark -
    now lit by a query,
    a burrow's remark.

                - written in the tunnel, somewhere between
                   127.0.0.1 and wherever you keep your data
"""


def cmd_dig(_args: argparse.Namespace) -> None:
    for line in POEM.splitlines():
        print(line)
        time.sleep(0.04)
