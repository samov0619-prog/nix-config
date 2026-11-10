"""Check installed Blueman Polkit support and unchanged upstream policy, offline."""

import argparse
import ast
from pathlib import Path
import xml.etree.ElementTree as ET


def policy_defaults(path):
    root = ET.parse(path).getroot()
    actions = {}
    for action in root.findall("action"):
        identifier = action.attrib["id"]
        if identifier in actions:
            raise ValueError(f"Duplicate policy action: {identifier}")
        defaults = action.find("defaults")
        if defaults is None:
            raise ValueError(f"Missing defaults: {identifier}")
        actions[identifier] = [(entry.tag, entry.text) for entry in defaults]
    if not actions:
        raise ValueError("No Polkit actions installed")
    return actions


def verify(package, source):
    constants = list(package.glob("lib/python*/site-packages/blueman/Constants.py"))
    if len(constants) != 1:
        raise ValueError("Expected one installed Blueman Constants.py")
    tree = ast.parse(constants[0].read_text())
    flags = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "POLKIT"
                for target in node.targets)
    ]
    if len(flags) != 1 or flags[0] is not True:
        raise ValueError("Installed Blueman must have POLKIT=True")

    upstream = source / "data/configs"
    installed = package / "share/polkit-1"
    if policy_defaults(installed / "actions/org.blueman.policy") != policy_defaults(
        upstream / "org.blueman.policy.in"
    ):
        raise ValueError("Installed action defaults differ from upstream")
    if (installed / "rules.d/blueman.rules").read_bytes() != (
        upstream / "blueman.rules"
    ).read_bytes():
        raise ValueError("Installed rules differ from upstream")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    verify(args.package, args.source)
    print("Blueman POLKIT=True; upstream action defaults and rules preserved")
