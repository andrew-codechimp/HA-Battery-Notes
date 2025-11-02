"""Battery library document generator."""

import json

from pytablewriter import MarkdownTableWriter


def get_device_list() -> None:
    """Sort the device library JSON file."""
    # Load the existing JSON library file
    with open(
        file="library/library.json",
        encoding="UTF-8",
    ) as f:
        devices_json = json.loads(f.read())
        devices = devices_json.get("devices")

    # Sort the devices by manufacturer and model
    devices.sort(
        key=lambda k: (
            k["manufacturer"].lower(),
            k.get("model_match_method", "").lower(),
            k["model"].lower(),
            k.get("model_id", "").lower(),
            k.get("hw_version", "").lower(),
        )
    )
    with open("library/library.json", "w", encoding="UTF-8") as f:
        f.write(json.dumps(devices_json, indent=4))


def regenerate_device_list() -> None:
    """Generate static file containing the device library."""

    # Load the existing JSON library file
    with open("library/library.json", encoding="UTF-8") as file:
        devices_json = json.loads(file.read())
        devices = devices_json.get("devices")

    rows = []
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

    writer = MarkdownTableWriter()
    writer.header_list = [
        "Manufacturer",
        "Model",
        "Battery Type",
        "Model ID (optional)",
        "HW Version (optional)",
    ]
    writer.value_matrix = rows

    tables_output = [f"## {len(devices)} Devices in library\n\n"]
    tables_output.append("This file is auto generated, do not modify\n\n")
    tables_output.append(
        "Request new devices to be added to the library [here](https://github.com/andrew-codechimp/HA-Battery-Notes/issues/new?template=new_device_request.yml&title=%5BDevice%5D%3A+)\n\n"
    )
    tables_output.append(writer.dumps())

    with open("library.md", "w", encoding="UTF-8") as md_file:
        md_file.write("".join(tables_output))
        md_file.close()


if __name__ == "__main__":
    get_device_list()
    regenerate_device_list()
