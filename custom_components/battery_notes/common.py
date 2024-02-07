"""Common functions for battery_notes."""


def isfloat(num):
    """Is the value a float."""
    if num:
        try:
            float(num)
            return True
        except ValueError:
            return False
    return False
