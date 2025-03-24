"""Battery library document generator."""

from __future__ import annotations

import json

from pytablewriter import MarkdownTableWriter


def generate_device_list():
    """Generate static file containing the device library."""

    # Load the existing JSON library file
    with open(
        "library/library.json", encoding="UTF-8"
    ) as f:
        devices_json = json.loads(f.read())
        devices = devices_json.get("devices")

    toc_links: list[str] = []
    tables_output: str = ""
    rows = []

    num_devices = len(devices)

    writer = MarkdownTableWriter()
    headers = [
        "Manufacturer",
        "Model",
        "Battery Type",
        "Model ID (optional)",
        "HW Version (optional)",
    ]

    writer.header_list = headers

    for device in devices:
        if device.get("battery_quantity", 1) > 1:
            battery_type_qty = f"{device['battery_quantity']}× {device['battery_type']}"
        else:
            battery_type_qty = device["battery_type"]

        model = device["model"]
        model_match_method = device.get("model_match_method", "")
        if model_match_method == "startswith":
            model = rf"{model}\*"
        if model_match_method == "endswith":
            model = rf"\*{model}"
        if model_match_method == "contains":
            model = rf"\*{model}\*"

        row = [
            device["manufacturer"],
            model,
            battery_type_qty,
            device.get("model_id", ""),
            device.get("hw_version", ""),
        ]
        rows.append(row)

    writer.value_matrix = rows
    tables_output += f"## {num_devices} Devices in library\n\n"
    tables_output += "This file is auto generated, do not modify\n\n"
    tables_output += "Request new devices to be added to the library [here](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=%5BDevice%5D%3A+)\n\n"
    tables_output += writer.dumps()

    with open("library.md", "w", encoding="UTF-8") as md_file:
        md_file.write("".join(toc_links) + tables_output)
        md_file.close()


generate_device_list()
