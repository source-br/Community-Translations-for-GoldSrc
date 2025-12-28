import os
import shutil
import tempfile
import time
import subprocess
import re 

from .path_utils import normalize_path


def delete_duplicate_textures(temp_dir: str, source_dir: str, settings: dict):
    source_names = {
        os.path.splitext(f)[0].lower()
        for f in os.listdir(source_dir)
        if f.lower().endswith("." + settings["format_type"])
    }

    for file in os.listdir(temp_dir):
        name, ext = os.path.splitext(file)
        if name.lower() in source_names and ext.lower() in [".bmp", ".png"]:
            os.remove(os.path.join(temp_dir, file))


def copy_texture_files(destination: str, source: str = None, individual_files: list = None, settings: dict = None):
    extension = "." + settings["format_type"]
    if source and os.path.exists(source):
        for file in os.listdir(source):
            if file.lower().endswith(extension):
                shutil.copy(normalize_path(os.path.join(source, file), settings), normalize_path(destination, settings))
    if individual_files:
        for file in individual_files:
            file = normalize_path(file, settings)
            if os.path.exists(file) and file.lower().endswith(extension):
                shutil.copy(file, normalize_path(destination, settings))


def create_wad(wadmaker_path: str, temp_dir: str, destination_wad: str, settings: dict, T: dict, run_with_spinner):
    wadmaker_path = normalize_path(wadmaker_path, settings)
    temp_dir = normalize_path(temp_dir, settings)
    destination_wad = normalize_path(destination_wad, settings)
    wad_basename = os.path.basename(destination_wad)
    msg = T.get("generating_wad", "Generating WAD: {name}").format(name=wad_basename)
    run_with_spinner([wadmaker_path, "-full", temp_dir], msg) 
    generated_wad = os.path.join(os.path.dirname(temp_dir), os.path.basename(temp_dir) + ".wad")
    shutil.move(generated_wad, destination_wad)


def create_qlumpy(qlumpy_path: str, ls_files: str, output_qlumpy: str, settings: dict, base_dir: str, T: dict, run_with_spinner):
    """
    Prepara arquivos .ls substituindo placeholders e executa o `qlumpy.exe`.
    """
    if not ls_files:
        return

    qlumpy_path = normalize_path(qlumpy_path, settings)
    if not os.path.exists(qlumpy_path):
        raise FileNotFoundError(f"qlumpy executable not found: {qlumpy_path}")

    output_dir = normalize_path(output_qlumpy, settings)
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception:
        parent = os.path.dirname(output_dir)
        if parent:
            os.makedirs(parent, exist_ok=True)

    tmp_dir = tempfile.mkdtemp(prefix="qlumpy_")

    # helpers
    def _replacements():
        return {
            "{{LANG}}": settings.get("lang_folder", ""),
            "{{Translated}}": settings.get("lang_folder_translated", ""),
            "{{Compilation}}": settings.get("lang_folder_compilation", ""),
            "{{FORMAT}}": settings.get("format_type", ""),
            "{{ROOT}}": settings.get("compilation_root", ""),
            "{{REPO}}": base_dir,
        }

    def _read_file(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()

    def _write_file(path, content):
        # Salva o .ls em ANSI (latin-1) para o qlumpy
        try:
            with open(path, "w", encoding="latin-1") as f:
                f.write(content)
        except Exception:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    replacements = _replacements()
    generated = []
    wad_names = [] 

    # 1. Processamento e Substituição de Placeholders nos Arquivos .ls
    for entry in ls_files.split(","):
        src_template = entry.strip()
        if not src_template:
            continue
        for k, v in replacements.items():
            src_template = src_template.replace(k, v)
        src_path = normalize_path(src_template, settings)
        if not os.path.exists(src_path):
            continue
        
        content = _read_file(src_path)
        
        # Extrai o nome do WAD para o log
        dest_match = re.search(r'^\s*\$DEST\s+"([^"]+)"', content, flags=re.IGNORECASE | re.MULTILINE)
        if dest_match:
            wad_names.append(dest_match.group(1))
        
        for k, v in replacements.items():
            content = content.replace(k, v)
        
        # Garante que referências de formato sejam bmp
        content = content.replace("{{FORMAT}}", "bmp")

        dest_name = os.path.basename(src_path)
        dest_path = os.path.join(tmp_dir, dest_name)
        _write_file(dest_path, content) 
        generated.append(dest_path)

    if not generated:
        shutil.rmtree(tmp_dir)
        return

    # 2. Configurações de execução
    run_cwd = normalize_path(base_dir, settings) or os.getcwd()
    debug_qlumpy = bool(settings.get('debug_qlumpy', False))
    mtime_window = int(settings.get('qlumpy_mtime_window', 3))
    
    # 3. Execução do qlumpy
    
    # Define a mensagem de status (Generating: nome.wad)
    if wad_names:
        display_name = ', '.join(sorted(list(set(wad_names))))
    else:
        display_name = T.get('wad_files', 'WAD files')
        
    msg = T.get('generating_wad_qlumpy', 'Generating: {name}').format(name=display_name)
    
    start_time = time.time()
    old_cwd = os.getcwd()
    
    # Prepara o comando
    if os.name == 'nt':
        args = ' '.join(f'"{p}"' for p in generated)
        cmd = f'"{qlumpy_path}" {args}'
        shell_exec = True
    else:
        cmd = [qlumpy_path] + generated
        shell_exec = False
        
    run_command_repr = cmd if shell_exec else ' '.join(f'"{x}"' for x in cmd)

    print(msg) # Imprime a mensagem de status

    try:
        # Mudar para o diretório de execução (base_dir)
        os.chdir(run_cwd)
        
        # USO DE subprocess.run()
        result = subprocess.run(
            cmd,
            cwd=run_cwd,
            shell=shell_exec,
            capture_output=True,
            text=True,
            encoding='latin-1',
            errors='replace'
        )
        
        rc = result.returncode
        stderr = result.stderr
        
        if rc != 0:
            # Tratar erro de execução
            cmd_repr = run_command_repr if 'run_command_repr' in locals() and run_command_repr else '<unknown>'
            
            # Lança o erro apenas com o que é necessário
            raise RuntimeError(f"{msg} failed (exit {rc}). Command: {cmd_repr}\nstderr:\n{stderr}")
            
    except Exception as e:
        raise e
    finally:
        os.chdir(old_cwd) # Volta ao diretório de trabalho original

    # 4. Fallback: Mover WADs declarados em $DEST ou por mtime
    
    # Tentativa de mover WADs declarados em $DEST "name.wad" nos arquivos .ls
    try:
        dest_names = []
        for name in wad_names:
            if name:
                dest_names.append(name)

        if dest_names:
            moved = []
            base_candidate = normalize_path(base_dir, settings)
            for name in set(dest_names):
                candidates = [os.path.join(run_cwd, name)]
                if base_candidate:
                    candidates.append(os.path.join(base_candidate, name))
                found_path = None
                
                for c in candidates:
                    if c and os.path.exists(c):
                        found_path = c
                        break
                
                if not found_path:
                    for root, _, files in os.walk(run_cwd):
                        if name in files:
                            found_path = os.path.join(root, name)
                            break
                            
                if found_path:
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        # *** AQUI: USA shutil.move() em vez de shutil.copy2() ***
                        shutil.move(found_path, os.path.join(output_dir, os.path.basename(found_path)))
                        moved.append(found_path)
                    except Exception:
                        pass
                        
            if moved:
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    pass
                return
    except Exception:
        pass

    # Fallback final: mover WADs por mtime (busca mais ampla, pós-execução)
    try:
        created_wads = []
        seen = set()
        candidates = [run_cwd, normalize_path(base_dir, settings)]
        for d in candidates:
            if not d or not os.path.isdir(d):
                continue
            for f in os.listdir(d):
                if not f.lower().endswith('.wad'):
                    continue
                fp = os.path.join(d, f)
                try:
                    mtime = os.path.getmtime(fp)
                except Exception:
                    continue
                
                if mtime >= start_time - mtime_window and fp not in seen:
                    seen.add(fp)
                    created_wads.append(fp)
                    
        for wad in created_wads:
            try:
                dest = os.path.join(output_dir, os.path.basename(wad))
                # *** AQUI: USA shutil.move() em vez de shutil.copy2() ***
                shutil.move(wad, dest)
            except Exception as e:
                 if debug_qlumpy:
                    print(f"Debug: Failed to move WAD by mtime: {wad}. Error: {e}")
                 pass
    finally:
        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass