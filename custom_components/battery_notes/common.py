"""Common functions for battery_notes."""


def isfloat(num):
    """Is the value a float."""
    try:
        float(num)
        return True
    except ValueError:
        return False
