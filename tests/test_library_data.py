"""Tests for the bundled device library data."""

import json
from collections import defaultdict
from pathlib import Path

LIBRARY_FILE = Path("library/library.json")


def test_no_conflicting_devices() -> None:
    """Test no two entries match the same device with different batteries.

    Matching treats such entries as ambiguous, so the device is never matched.
    Devices with variants using different batteries should use a MANUAL battery type.
    """
    batteries: defaultdict[tuple, set[tuple[str, int]]] = defaultdict(set)
    for device in json.loads(LIBRARY_FILE.read_text())["devices"]:
        key = (
            device["manufacturer"].casefold(),
            device["model"].casefold(),
            (device.get("model_id") or "").casefold(),
            (device.get("hw_version") or "").casefold(),
            device.get("model_match_method"),
        )
        batteries[key].add((device["battery_type"], device.get("battery_quantity", 1)))

    conflicts = {key: found for key, found in batteries.items() if len(found) > 1}
    assert conflicts == {}
