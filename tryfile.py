def print_colored(text, color):
    color_codes = {
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "magenta": "\033[95m",
    "cyan": "\033[96m",
    "white": "\033[97m",
    }
    return color_codes[color] + text
reset_code = "\033[0m"

print(print_colored("Hello, World!", "red"))