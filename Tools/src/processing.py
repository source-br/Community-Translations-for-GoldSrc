import os
import shutil
import tempfile
import subprocess
import configparser

from .path_utils import normalize_path, read_config_block
from .file_ops import delete_duplicate_textures, copy_texture_files, create_wad, create_qlumpy
from .subprocess_utils import run_with_spinner


def process_section(section_name: str, config: configparser.ConfigParser, settings: dict, T: dict):
    source = None
    destination = None
    if "origem_folder" in config[section_name]:
        source = normalize_path(config[section_name]["origem_folder"], settings)
    if "destino_folder" in config[section_name]:
        destination = normalize_path(config[section_name]["destino_folder"], settings)

    # Seção voltada para geração via qlumpy (.ls) — não requer wad_path
    if "ls_files" in config[section_name] and "output_qlumpy" in config[section_name]:
        qlumpy_path = ""
        if "global" in config:
            qlumpy_path = normalize_path(config["global"].get("qlumpy_path", ""), settings)
        ls_files = config[section_name].get("ls_files", "")
        output_qlumpy = config[section_name].get("output_qlumpy", "")
        # calcula base_dir (repo root) relativo a este módulo: ../../
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        create_qlumpy(qlumpy_path, ls_files, output_qlumpy, settings, base_dir, T, run_with_spinner)
        return

    # Fluxo padrão: geração a partir de um WAD
    if "wad_path" not in config[section_name]:
        raise KeyError("wad_path")

    wad_path = normalize_path(config[section_name]["wad_path"], settings)
    psd_folder = normalize_path(config[section_name].get("psd_folder", ""), settings)
    psd_files = [normalize_path(file.strip(), settings) for file in config[section_name].get("psd_files", "").split(",") if file.strip()]
    output_folder = normalize_path(config[section_name]["output_folder"], settings)
    wadmaker_path = normalize_path(config["global"]["wadmaker_path"], settings)

    wad_name = os.path.splitext(os.path.basename(wad_path))[0]
    temp_dir = os.path.join(tempfile.gettempdir(), wad_name)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        wad_basename = os.path.basename(wad_path)
        msg = T.get("extracting_wad", "Extracting WAD: {name}").format(name=wad_basename)
        run_with_spinner([wadmaker_path, "-overwrite", "-indexed", "-format", "bmp", "-nologfile", wad_path, temp_dir], msg)
        delete_duplicate_textures(temp_dir, psd_folder, settings)
        copy_texture_files(temp_dir, psd_folder, psd_files, settings)
        wad_name = os.path.splitext(os.path.basename(wad_path))[0]
        final_destination = os.path.join(output_folder, wad_name + ".wad")
        create_wad(wadmaker_path, temp_dir, final_destination, settings, T, run_with_spinner)
    finally:
        shutil.rmtree(temp_dir)


def process_bsp_section(section_name: str, config: configparser.ConfigParser, settings: dict, T: dict):
    bsp_path = normalize_path(config[section_name]["bsp_folder"], settings)
    psd_folder = normalize_path(config[section_name].get("psd_folder", ""), settings)
    psd_files = [normalize_path(file.strip(), settings) for file in config[section_name].get("psd_files", "").split(",") if file.strip()]
    output_bsp_folder = normalize_path(config[section_name]["output_bsp_folder"], settings)
    bspguy = normalize_path(config["global"]["bspguy_path"], settings)
    wadmaker_path = normalize_path(config["global"]["wadmaker_path"], settings)

    if not os.path.exists(bsp_path):
        print(f"{T['error_bsp_not_found']} {bsp_path}")
        return
    if not os.path.exists(bspguy):
        print(f"{T['error_bspguy_path_invalid']} {bspguy}")
        return

    temp_dir = tempfile.mkdtemp()
    bsp_name = os.path.basename(bsp_path)
    temp_bsp_path = os.path.join(temp_dir, bsp_name)
    texture_dir = os.path.join(temp_dir, "texture")

    try:
        shutil.copy(bsp_path, temp_bsp_path)
        os.makedirs(texture_dir, exist_ok=True)
        copy_texture_files(texture_dir, psd_folder, psd_files, settings)
        msg_wad = T.get("generating_wad", "Generating WAD: {name}").format(name=f"{bsp_name}.wad")
        run_with_spinner([wadmaker_path, "-full", texture_dir], msg_wad)

        generated_wad = texture_dir + ".wad"
        renamed_wad = temp_bsp_path + ".wad"

        if not os.path.exists(generated_wad):
            print(f"{T['error_wad_not_generated']} {generated_wad}")
            return

        shutil.move(generated_wad, renamed_wad)
        msg_bsp = T.get("generating_bsp", "Generating BSP: {name}").format(name=bsp_name)
        run_with_spinner([bspguy, "importwad", temp_bsp_path, "-i", renamed_wad], msg_bsp)

        final_destination = os.path.join(output_bsp_folder, bsp_name)
        shutil.copy2(temp_bsp_path, final_destination)

    except subprocess.CalledProcessError as e:
        print(f"{T['error_subprocess']} {e}")
    except Exception as e:
        print(f"{T['fatal_error']} {bsp_name}: {e}")
    finally:
        shutil.rmtree(temp_dir)


def load_groups_from_config(config_path: str):
    groups = {}
    current_group = None

    config_path = os.path.expanduser(config_path)
    config_path = os.path.abspath(config_path)

    if not os.path.exists(config_path):
        return groups

    with open(config_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                current_group = line[1:].strip()
                groups[current_group] = []
            elif line.startswith("[") and line.endswith("]"):
                if current_group is not None:
                    section = line[1:-1].strip()
                    groups[current_group].append(section)
            else:
                pass

    return groups


def compile_all_wads(config_path: str, settings: dict, T: dict):
    config = read_config_block(config_path)
    if "global" not in config or "wadmaker_path" not in config["global"]:
        print(T["error_config"])
        input("\n" + T["completed"])
        return

    for section in config.sections():
        if section.lower() == "global":
            continue
        try:
            if "bsp_folder" in config[section]:
                process_bsp_section(section, config, settings, T)
            else:
                process_section(section, config, settings, T)
        except Exception as e:
            print(f"{T['error_section']} [{section}]: {e}")
    input("\n" + T["completed"])


def compile_only_bsps(config_path: str, settings: dict, T: dict):
    config = read_config_block(config_path)
    groups = load_groups_from_config(config_path)

    filtered_groups = {}
    for group_name, sections in groups.items():
        for section in sections:
            if section in config and "bsp_folder" in config[section]:
                filtered_groups.setdefault(group_name, []).append(section)

    return filtered_groups


def compile_bsp_group(group_name: str, sections: list, config_path: str, settings: dict, T: dict):
    config = read_config_block(config_path)
    for section in sections:
        try:
            if "bsp_folder" in config[section]:
                process_bsp_section(section, config, settings, T)
        except Exception as e:
            print(f"Error compiling section {section}: {e}")


def compile_only_wads(config_path: str, settings: dict, T: dict):
    config = read_config_block(config_path)
    if "global" not in config or "wadmaker_path" not in config["global"]:
        print(T["error_config"])
        input("\n" + T["completed"])
        return

    groups = load_groups_from_config(config_path)

    filtered_groups = {}
    for group_name, sections in groups.items():
        for section in sections:
            if section in config and "bsp_folder" not in config[section]:
                filtered_groups.setdefault(group_name, []).append(section)

    return filtered_groups


def compile_game(config_path: str, group_name: str, settings: dict, T: dict):
    config = read_config_block(config_path)
    groups = load_groups_from_config(config_path)

    if group_name not in groups:
        print(f"[Error] Grupo não encontrado: {group_name}")
        return

    sections = groups[group_name]
    for section in sections:
        try:
            if section not in config:
                print(f"[Warning] Seção {section} não encontrada no config principal. Pulando.")
                continue

            if "bsp_folder" in config[section]:
                process_bsp_section(section, config, settings, T)
            else:
                process_section(section, config, settings, T)
        except Exception as e:
            print(f"{T.get('error_section','Error processing section')} [{section}]: {e}")
