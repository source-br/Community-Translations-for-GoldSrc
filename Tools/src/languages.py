import os
import shutil
import configparser

from .translations import TRANSLATIONS


def add_new_language(base_lang="Original", T: dict = None):
    # usa T fornecido (passado pela interface). Se não fornecido, fallback para pt/en.
    if T is None:
        T = TRANSLATIONS.get("pt", TRANSLATIONS.get("en", {}))
    os.system("cls" if os.name == "nt" else "clear")
    print(T.get("add_new_language_header", "=== Add New Language ===") + "\n")

    default_project = os.getcwd()

    # Pastas que NÃO serão mostradas ao escolher projeto
    hidden_folders = {"__pycache__", "UI", "Tools", ".git", "Docs", "svencoop"}
    hidden_lower = {h.lower() for h in hidden_folders}

    # Lista subpastas do diretório atual como possíveis projetos (filtrando as ocultas)
    try:
        subdirs = [
            d for d in os.listdir(default_project)
            if os.path.isdir(os.path.join(default_project, d)) and d.lower() not in hidden_lower
        ]
    except Exception:
        subdirs = []

    if subdirs:
        print(T.get("projects_found", "Projetos encontrados no diretório atual:"))
        for i, d in enumerate(subdirs, start=1):
            print(f"{i}. {d}")
        # Oferecer opção de voltar com 'V'
        print(f"V. {T.get('back_label','Back')}")
        selection = input(T.get("projects_selection", f"Escolha o projeto (1-{len(subdirs)}) [1]: ").format(count=len(subdirs))).strip()
        if selection.strip().upper() == "V":
            return
        if selection == "":
            selection = "1"
        try:
            sel_i = int(selection)
            if 1 <= sel_i <= len(subdirs):
                project_root = os.path.join(default_project, subdirs[sel_i - 1])
            else:
                print("[Aviso] Seleção inválida. Usando diretório atual.")
                project_root = default_project
        except ValueError:
            print("[Aviso] Entrada inválida. Usando diretório atual.")
            project_root = default_project
    else:
        project_input = input(f"Project root path (ex: a:\\\\path\\\\to\\\\valve) [{default_project}] (V para voltar): ").strip()
        if project_input.strip().upper() == "V":
            return
        project_root = project_input if project_input else default_project

    project_root = os.path.expanduser(project_root)
    project_root = os.path.abspath(project_root)

    if not os.path.isdir(project_root):
        print(f"[Error] Project root inválido ou não encontrado: {project_root}")
        return

    lang_id = input(T.get("enter_language_id", "New language ID (e.g. RU, FR, ES): ")).strip()
    if not lang_id:
        print("[Error] Invalid language ID.")
        return
    lang_id = lang_id.upper()

    lang_ini_path = os.path.join(os.getcwd(), "language.ini")
    cfg = configparser.ConfigParser()
    english_name = ""
    native_name = ""
    compilation_name = ""
    translation_name = ""
    if os.path.exists(lang_ini_path):
        cfg.read(lang_ini_path, encoding="utf-8")
        if lang_id in cfg.sections():
            sec = cfg[lang_id]
            english_name = sec.get("EnglishName", "") or ""
            native_name = sec.get("NativeName", "") or ""
            compilation_name = sec.get("CompilationFolder", "") or ""
            translation_name = sec.get("TranslationFolder", "") or ""
            print(T.get("info_existing_entry", "[Info] Found existing entry for {lang} in {path}; values will be used as defaults.").format(lang=lang_id, path=lang_ini_path))

    inp = input(T.get("prompt_english_name", "Language English name (e.g. Russian) [{default}]: ").format(default=english_name)).strip()
    if inp:
        english_name = inp
    inp = input(T.get("prompt_native_name", "Language native name (e.g. русский) [{default}]: ").format(default=native_name)).strip()
    if inp:
        native_name = inp

    # Não perguntar mais pelo nome das pastas Compilation/Translation — usa valores lidos do language.ini
    # ou os defaults estáticos
    if not compilation_name:
        compilation_name = "Compilation"
    if not translation_name:
        translation_name = "Translation"

    base_lang_path = os.path.join(project_root, base_lang)
    new_lang_path = os.path.join(project_root, lang_id)

    if os.path.exists(new_lang_path):
        print(f"[Error] Language folder {lang_id} already exists at: {new_lang_path}")
        return

    if not os.path.exists(base_lang_path):
        print(f"[Error] Base language folder not found in project: {base_lang_path}")
        return

    try:
        os.makedirs(new_lang_path, exist_ok=True)
        comp_path = os.path.join(new_lang_path, compilation_name)
        trans_path = os.path.join(new_lang_path, translation_name)
        os.makedirs(comp_path, exist_ok=True)
        os.makedirs(trans_path, exist_ok=True)

        # cria subpasta <nome_do_projeto>_addon dentro de Compilation
        addon_folder_name = f"{os.path.basename(project_root)}_addon"
        addon_base = os.path.join(comp_path, addon_folder_name)
        os.makedirs(addon_base, exist_ok=True)

        # copia conteúdo de base_lang para trans_path, evitando arquivos .wav e pasta 'wav'
        for item in os.listdir(base_lang_path):
            if item.lower() == "psds" or item.lower() == "wav":
                continue
            src = os.path.join(base_lang_path, item)
            dst = os.path.join(trans_path, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('*.wav'))
            else:
                if src.lower().endswith(".wav"):
                    continue
                shutil.copy2(src, dst)

        # move arquivos não-BMP de trans_path para addon (mantendo regra mdl->models)
        for root, _, files in os.walk(trans_path):
            rel_root = os.path.relpath(root, trans_path)
            if rel_root != "." and rel_root.split(os.sep)[0].lower() == "wav":
                continue
            for fname in files:
                lower = fname.lower()
                if lower.endswith(".bmp") or lower.endswith(".wav"):
                    continue
                src_file = os.path.join(root, fname)
                rel_dir = os.path.relpath(root, trans_path)
                if rel_dir == ".":
                    target_dir = os.path.join(addon_base, os.path.splitext(fname)[0])
                else:
                    parts = rel_dir.split(os.sep)
                    if parts and parts[0].lower() == "mdl":
                        parts = parts[1:]
                    new_rel = os.path.join(*parts) if parts else ""
                    target_dir = os.path.join(addon_base, new_rel) if new_rel else addon_base
                os.makedirs(target_dir, exist_ok=True)
                try:
                    shutil.move(src_file, os.path.join(target_dir, fname))
                except Exception:
                    pass

        # --- copiar/mesclar a partir de UI/Translations/Goldsrc/<project_name>/Original para UI/.../<project_name>/<lang_id>/ ---
        try:
            project_name = os.path.basename(project_root)
            ui_lang_root = os.path.join(os.getcwd(), "UI", "Translations", "Goldsrc", project_name, lang_id)
            os.makedirs(ui_lang_root, exist_ok=True)

            dst_trans = os.path.join(ui_lang_root, translation_name)
            dst_comp = os.path.join(ui_lang_root, compilation_name)
            if os.path.exists(dst_trans):
                shutil.rmtree(dst_trans)
            os.makedirs(dst_trans, exist_ok=True)
            if os.path.exists(dst_comp):
                shutil.rmtree(dst_comp)
            os.makedirs(dst_comp, exist_ok=True)

            src_original = os.path.join(os.getcwd(), "UI", "Translations", "Goldsrc", project_name, "Original")
            if os.path.exists(src_original):
                for root, dirs, files in os.walk(src_original):
                    rel_root = os.path.relpath(root, src_original)
                    if rel_root != "." and rel_root.split(os.sep)[0].lower() == "wav":
                        continue
                    # destino dentro de Translation (preserva estrutura relativa)
                    dest_dir = os.path.join(dst_trans, rel_root) if rel_root != "." else dst_trans
                    os.makedirs(dest_dir, exist_ok=True)
                    for f in files:
                        if f.lower().endswith(".wav"):
                            continue
                        src_file = os.path.join(root, f)
                        # .md -> copiar para raiz da sigla como translations.md (ou with suffix)
                        if f.lower().endswith(".md"):
                            base_name = "translations.md"
                            target_path = os.path.join(ui_lang_root, base_name)
                            if os.path.exists(target_path):
                                idx = 1
                                while True:
                                    alt = os.path.join(ui_lang_root, f"translations_{idx}.md")
                                    if not os.path.exists(alt):
                                        target_path = alt
                                        break
                                    idx += 1
                            try:
                                shutil.copy2(src_file, target_path)
                            except Exception:
                                pass
                        else:
                            dst_file = os.path.join(dest_dir, f)
                            try:
                                shutil.copy2(src_file, dst_file)
                            except Exception:
                                pass

                # mover quaisquer .md remanescentes dentro das subpastas para a raiz da sigla (ui_lang_root)
                for root, _, files in os.walk(ui_lang_root):
                    for fname in files:
                        if not fname.lower().endswith(".md"):
                            continue
                        full = os.path.join(root, fname)
                        rel_to_lang_root = os.path.relpath(full, ui_lang_root)
                        if os.path.dirname(rel_to_lang_root) == "." and fname.lower().startswith("translations"):
                            continue
                        base_name = "translations.md"
                        target = os.path.join(ui_lang_root, base_name)
                        if os.path.abspath(full) == os.path.abspath(target):
                            continue
                        if os.path.exists(target):
                            idx = 1
                            while True:
                                alt = os.path.join(ui_lang_root, f"translations_{idx}.md")
                                if not os.path.exists(alt):
                                    target = alt
                                    break
                                idx += 1
                        try:
                            shutil.move(full, target)
                        except Exception:
                            pass

            # renomeia "manoso arquivo.md" para "tradução.md" dentro da pasta da sigla do idioma
            for root, _, files in os.walk(ui_lang_root):
                for fname in files:
                    if fname.lower() == "manoso arquivo.md":
                        oldpath = os.path.join(root, fname)
                        newpath = os.path.join(root, "tradução.md")
                        try:
                            if os.path.exists(newpath):
                                os.remove(newpath)
                            os.rename(oldpath, newpath)
                        except Exception:
                            pass
        except Exception:
            pass
        # --- FIM: cópia para UI/Translations ---

        if not os.path.exists(lang_ini_path):
            with open(lang_ini_path, "w", encoding="utf-8") as f:
                f.write("")
        cfg.read(lang_ini_path, encoding="utf-8")
        if lang_id not in cfg.sections():
            cfg[lang_id] = {}
        cfg[lang_id]["ID"] = lang_id
        cfg[lang_id]["EnglishName"] = english_name
        cfg[lang_id]["NativeName"] = native_name
        with open(lang_ini_path, "w", encoding="utf-8") as f:
            cfg.write(f)

        print(T.get("success_language_added", "✅ Language {lang} added successfully!").format(lang=lang_id))
        print(T.get("success_created_at", "📁 Created at: {path}").format(path=new_lang_path))
        print(T.get("success_registry_updated", "Language registry updated at: {path}").format(path=lang_ini_path))
    except Exception as e:
        print(f"[Error] Failed to add language: {e}")
