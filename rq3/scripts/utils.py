import json

def load_json(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        return json.load(f)
    
def percentage(value, total):
    return value / total * 100

def get_text_color(hex_color):
    """
    Returns white text for dark colors and black text for light colors.
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return "white" if luminance < 0.5 else "black"