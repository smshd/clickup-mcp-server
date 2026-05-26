"""Natural language color names to hex codes for ClickUp tags."""

COLOR_MAP = {
    "dark blue": "#04A9F4",
    "blue": "#2196F3",
    "light blue": "#73D8FF",
    "turquoise": "#00BCD4",
    "dark green": "#4CAF50",
    "green": "#8BC34A",
    "light green": "#CDDC39",
    "yellow": "#FFEB3B",
    "orange": "#FF9800",
    "dark orange": "#FF5722",
    "red": "#f44336",
    "pink": "#E91E63",
    "purple": "#9C27B0",
    "dark purple": "#673AB7",
    "grey": "#9E9E9E",
    "gray": "#9E9E9E",
    "dark grey": "#607D8B",
    "dark gray": "#607D8B",
    "brown": "#795548",
    "black": "#333333",
    "white": "#FFFFFF",
}


def resolve_color(color: str) -> str:
    """
    Resolve a color name or hex code to a hex code.

    Accepts:
    - Hex codes: "#FF5722" (pass-through)
    - Natural language: "dark blue", "red", "light green"

    Returns hex code string.
    """
    if not color:
        return ""
    color = color.strip()
    if color.startswith("#"):
        return color
    return COLOR_MAP.get(color.lower(), color)
