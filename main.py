import os
import platform
from Tools.src.translations import TRANSLATIONS

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(
    BASE_DIR,
    "Tools",
    "Compilator",
    "config-windows.ini" if platform.system() == "Windows" else "config-linux.ini"
)
SETTINGS_PATH = os.path.join(BASE_DIR, "Tools", "Compilator", "settings.ini")

# valores iniciais
settings = {
    "language": "en",
    "lang_folder": "EN",
    "lang_folder_compilation": "Compilation",
    "lang_folder_translated": "Translation",
    "format_type": "bmp",
    "format_folder": "bmp"
}

if __name__ == "__main__":
    import Tools.src.functions as functions
    import Tools.src.interface as interface
    interface.start(settings, BASE_DIR, CONFIG_PATH, SETTINGS_PATH, TRANSLATIONS, functions)