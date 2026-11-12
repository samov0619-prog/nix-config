"""Dismiss only active Mako notifications matching an exact app/category pair."""

import argparse
import json
import subprocess
import sys


def close(makoctl, app_name, category):
    result = subprocess.run(
        [makoctl, "list", "-j"], capture_output=True, text=True, check=True, timeout=5
    )
    notifications = json.loads(result.stdout)
    if not isinstance(notifications, list):
        raise ValueError("Unexpected Mako notification list")
    for notification in notifications:
        if not isinstance(notification, dict):
            raise ValueError("Unexpected Mako notification entry")
        if (notification.get("app_name"), notification.get("category")) != (
            app_name, category
        ):
            continue
        identifier = notification.get("id")
        if type(identifier) is not int or not 0 < identifier <= 0xFFFFFFFF:
            raise ValueError("Invalid Mako notification ID")
        subprocess.run(
            [makoctl, "dismiss", "-n", str(identifier)], check=True, timeout=5
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--makoctl", required=True)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--category", required=True)
    args = parser.parse_args()
    try:
        close(args.makoctl, args.app_name, args.category)
    except (OSError, ValueError, subprocess.SubprocessError):
        # Never print the notification list or unrelated notification bodies.
        print("Could not close the selected notification", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
