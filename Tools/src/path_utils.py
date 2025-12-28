import os
import configparser


def normalize_path(path: str, settings: dict) -> str:
    path = path.replace("{{ROOT}}", settings.get("compilation_root", "")) \
               .replace("{{LANG}}", settings.get("lang_folder", "")) \
               .replace("{{Translated}}", settings.get("lang_folder_translated", "")) \
               .replace("{{Compilation}}", settings.get("lang_folder_compilation", "")) \
               .replace("{{FORMAT}}", settings.get("format_folder", ""))
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    return path


def read_config_block(config_path: str):
    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")
    return parser
