"""
Compat layer: re-exporta funções agrupadas em módulos menores.
Mantém API antiga (import Tools.src.functions as functions).
"""

from .translations import TRANSLATIONS

# path utilities
from .path_utils import normalize_path, read_config_block

# subprocess / spinner
from .subprocess_utils import run_with_spinner, debug_message

# file operations
from .file_ops import delete_duplicate_textures, copy_texture_files, create_wad, create_qlumpy

# processing and compilation
from .processing import (
    process_section,
    process_bsp_section,
    load_groups_from_config,
    compile_all_wads,
    compile_only_bsps,
    compile_bsp_group,
    compile_only_wads,
    compile_game,
)

# links and languages
from .links import create_links
from .languages import add_new_language

__all__ = [
    "normalize_path",
    "read_config_block",
    "run_with_spinner",
    "debug_message",
    "delete_duplicate_textures",
    "copy_texture_files",
    "create_wad",
    "create_qlumpy",
    "process_section",
    "process_bsp_section",
    "load_groups_from_config",
    "compile_all_wads",
    "compile_only_bsps",
    "compile_bsp_group",
    "compile_only_wads",
    "compile_game",
    "create_links",
    "add_new_language",
    "TRANSLATIONS",
]