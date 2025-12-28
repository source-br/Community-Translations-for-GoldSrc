import os
import re
import configparser
from .translations import TRANSLATIONS  # usado como fallback inicial se necessário

def build_select_prompt(T: dict, max_number: int = None, prefix: str = "") -> str:
    """
    Constrói prompt de seleção usando a string base T['select'] e, se fornecido,
    adiciona o intervalo numérico (1-max_number). Não altera textos com letras
    (por exemplo A/V), apenas adiciona a indicação numérica quando apropriado.
    """
    base = T.get("select", "Select: ").rstrip()
    # remove eventuais ':' finais para normalizar
    if base.endswith(":"):
        base = base[:-1].rstrip()
    range_part = f" (1-{max_number})" if (isinstance(max_number, int) and max_number >= 1) else ""
    return prefix + base + range_part + ": "

def load_settings(settings: dict, SETTINGS_PATH: str, TRANSLATIONS: dict, functions_module=None, BASE_DIR: str = "."):
    """
    Carrega settings. Se não existir SETTINGS_PATH:
      1) pergunta idioma da interface (PT-BR / EN)
      2) com UI no idioma escolhido, pergunta idioma do projeto (lista em BASE_DIR/valve)
          - nessa segunda etapa há opção de 'Add new language' que chama functions_module.add_new_language
    Retorna dicionário de traduções (T).
    """
    config = configparser.ConfigParser()
    default_comp_root = r"C:\Program Files (x86)\Steam\steamapps\common"
    if os.path.exists(SETTINGS_PATH):
        # lê settings básicos
        config.read(SETTINGS_PATH, encoding="utf-8")
        settings["language"] = config.get("config", "language", fallback="en")
        settings["lang_folder"] = config.get("config", "lang_folder", fallback="EN")
        # defaults locais — valores finais de Compilation/Translation virão de language.ini quando disponível
        settings["lang_folder_compilation"] = config.get("config", "lang_folder_compilation", fallback="Compilation")
        settings["lang_folder_translated"] = config.get("config", "lang_folder_translated", fallback="Translated")
        settings["format_type"] = config.get("config", "format_type", fallback="psd").lower()
        settings["format_folder"] = config.get("config", "format_folder", fallback="PSD")
        # nova chave: raiz de instalação/compilation (ex: C:\Program Files (x86)\Steam\steamapps\common)
        settings["compilation_root"] = config.get("config", "compilation_root", fallback="").strip() or default_comp_root

        # se houver language.ini na raiz e existir seção para lang_folder, usar seus nomes
        try:
            lang_ini = os.path.join(os.getcwd(), "language.ini")
            if os.path.exists(lang_ini):
                langcfg = configparser.ConfigParser()
                langcfg.read(lang_ini, encoding="utf-8")
                sect = settings.get("lang_folder", "")
                if sect and sect in langcfg:
                    settings["lang_folder_compilation"] = langcfg[sect].get("CompilationFolder", settings["lang_folder_compilation"])
                    settings["lang_folder_translated"] = langcfg[sect].get("TranslationFolder", settings["lang_folder_translated"])
        except Exception:
            # mantém defaults caso falhe a leitura
            pass

        language = settings["language"]
        return TRANSLATIONS.get(language, TRANSLATIONS["en"])

    # Se não existir settings: usamos defaults fornecidos em `settings` (evita perguntar idioma da interface)
    # define valores padrão mínimos e salva, depois pede apenas a pasta de idioma do projeto
    settings.setdefault("language", settings.get("language", "en"))
    settings.setdefault("format_type", "bmp")
    settings.setdefault("format_folder", "bmp")
    if "compilation_root" not in settings or not settings.get("compilation_root"):
        settings["compilation_root"] = default_comp_root
    # salva settings iniciais
    save_settings(settings, SETTINGS_PATH)

    # carregar traduções de acordo com o idioma (não há prompt)
    language = settings["language"]
    T = TRANSLATIONS.get(language, TRANSLATIONS["en"])

    # Etapa 2 = escolher idioma do projeto (pasta sob BASE_DIR/valve)
    select_project_language(settings, SETTINGS_PATH, functions_module, BASE_DIR, T)
    return T

def save_settings(settings: dict, SETTINGS_PATH: str):
    """
    Salva apenas configurações de interface / formato e a pasta do idioma.
    Não persistir aqui Compilation/Translation — esses valores vêm do language.ini.
    """
    config = configparser.ConfigParser()
    config["config"] = {
        "language": settings["language"],
        "lang_folder": settings["lang_folder"],
        "format_type": settings["format_type"],
        "format_folder": settings["format_folder"],
        # salva a nova configuração
        "compilation_root": settings.get("compilation_root", "")
    }
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        config.write(f)

# NOTE: interface language is no longer selected interactively;
# defaults are provided and managed via settings.ini. The old
# `configure_language` interactive prompt was removed.

def select_project_language(settings: dict, SETTINGS_PATH: str, functions_module, BASE_DIR: str, T: dict):
    """
    Seletor interativo de pasta de idioma do projeto (procura em BASE_DIR/valve).
    Inclui opção para adicionar novo idioma (A).
    """
    while True:
        valve_dir = os.path.join(BASE_DIR, "valve")
        search_dir = valve_dir if os.path.isdir(valve_dir) else BASE_DIR
        try:
            all_dirs = [d for d in os.listdir(search_dir) if os.path.isdir(os.path.join(search_dir, d))]
        except Exception:
            all_dirs = []

        ignore_exact = {"docs", "psds", "original"}
        dirs = [d for d in all_dirs if d and not d.startswith(".") and d.lower() not in ignore_exact]
        dirs.sort()

        print("\n" + T.get("choose_lang_folder_found", "Choose project language folder (found in: {path}):").format(path=search_dir))
        for idx, d in enumerate(dirs, start=1):
            print(f"{idx}. {d}")
        print("A. " + T.get("add_new_language", "Add new language"))
        print("V. " + T.get("config_back", "Back"))

        sel = input(build_select_prompt(T, max_number=(len(dirs) if dirs else None), prefix="\n")).strip().upper()
        if sel == "V":
            # Se é a primeira configuração e usuário volta, apenas continua sem mudar (mantém defaults)
            return
        if sel == "A":
            if functions_module is None:
                print("[Error] functions module not available to add a new language.")
                input(T.get("press_enter", "Press Enter to continue..."))
                continue
            # Chama função interativa para criar novo idioma (usa base 'Original' por padrão)
            # passa o dicionário de traduções atual para que a função exiba as strings certas
            functions_module.add_new_language(base_lang="Original", T=T)
            # após adicionar, reitera para mostrar pastas atualizadas
            continue
        if sel.isdigit() and 1 <= int(sel) <= len(dirs):
            chosen = dirs[int(sel) - 1]
            settings["lang_folder"] = chosen
            # tentar obter nomes de Compilation/Translation do language.ini (se existir)
            try:
                lang_ini = os.path.join(os.getcwd(), "language.ini")
                if os.path.exists(lang_ini):
                    langcfg = configparser.ConfigParser()
                    langcfg.read(lang_ini, encoding="utf-8")
                    if chosen in langcfg:
                        settings["lang_folder_compilation"] = langcfg[chosen].get("CompilationFolder", settings.get("lang_folder_compilation", "Compilation"))
                        settings["lang_folder_translated"] = langcfg[chosen].get("TranslationFolder", settings.get("lang_folder_translated", "Translated"))
            except Exception:
                pass
            save_settings(settings, SETTINGS_PATH)
            print(T.get("folder_language_ok", "Language folder updated."))
            input(T.get("press_enter", "Press Enter to continue..."))
            return
        else:
            print(T["invalid"])
            input(T.get("press_enter", "Press Enter to continue..."))

def settings_menu(settings: dict, T: dict, SETTINGS_PATH: str, BASE_DIR: str, functions_module=None):
    """
    Menu de configurações:
    - opção 2: selector que lista pastas sob BASE_DIR (ex: pasta 'valve') para escolher a pasta de idioma
    - voltar: use 'V'
    """
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        current_format = settings.get("format_type", "psd").lower()
        compilation_root_display = settings.get("compilation_root", "") or "(not set)"
        print(T['config_title'])
        print(f"1. {T['config_folder']} ({settings.get('lang_folder', '')})")
        print(f"2. {T['config_format']} ({current_format})")
        print("3. " + T.get("add_new_language", "Add new language"))
        print(f"4. {T.get('config_compilation_root', 'Change compilation root')} ({compilation_root_display})")
        print("V. " + T["config_back"])
        option = input(T["config_choose"]).strip()

        if option == "1":
            # procura dentro de BASE_DIR/valve se existir, senão usa BASE_DIR
            valve_dir = os.path.join(BASE_DIR, "valve")
            search_dir = valve_dir if os.path.isdir(valve_dir) else BASE_DIR
            try:
                # lista apenas diretórios, ignora ocultos e entradas vazias
                all_dirs = [d for d in os.listdir(search_dir) if os.path.isdir(os.path.join(search_dir, d))]
            except Exception:
                all_dirs = []

            # Ignorar pastas exatas "Docs" e "PSDs" (case-insensitive) e entradas que começam com '.'
            ignore_exact = {"docs", "psds", "original"}
            dirs = [
                d for d in all_dirs
                if d and not d.startswith(".") and d.strip() and d.lower() not in ignore_exact
            ]
            dirs.sort()

            if not dirs:
                print(T.get("no_lang_folders", "No language folders found in project root."))
                input(T["press_enter"])
                continue

            print("\n" + T.get("choose_lang_folder_found", "Choose language folder (found in: {path}):").format(path=search_dir))
            for idx, d in enumerate(dirs, start=1):
                print(f"{idx}. {d}")
            print("V. " + T.get("config_back", "Back"))

            sel = input(build_select_prompt(T, max_number=len(dirs), prefix="\n")).strip().upper()
            if sel == "V":
                continue
            if sel.isdigit() and 1 <= int(sel) <= len(dirs):
                chosen = dirs[int(sel) - 1]
                # salva apenas o nome da pasta (ex: PT-BR, RU) para uso com {{LANG}}
                settings["lang_folder"] = chosen
                # tentar obter nomes de Compilation/Translation do language.ini (se existir)
                try:
                    lang_ini = os.path.join(os.getcwd(), "language.ini")
                    if os.path.exists(lang_ini):
                        langcfg = configparser.ConfigParser()
                        langcfg.read(lang_ini, encoding="utf-8")
                        if chosen in langcfg:
                            settings["lang_folder_compilation"] = langcfg[chosen].get("CompilationFolder", settings.get("lang_folder_compilation", "Compilation"))
                            settings["lang_folder_translated"] = langcfg[chosen].get("TranslationFolder", settings.get("lang_folder_translated", "Translated"))
                except Exception:
                    pass
                save_settings(settings, SETTINGS_PATH)
                print(T.get("folder_language_ok", "Language folder updated."))
            else:
                print(T["invalid"])
            input(T["press_enter"])
        elif option == "2":
            new_format = "bmp" if current_format == "psd" else "psd"
            settings["format_type"] = new_format
            settings["format_folder"] = new_format
            save_settings(settings, SETTINGS_PATH)
        elif option == "3":
            # chama função interativa para adicionar novo idioma (como na tela inicial)
            if functions_module is None:
                print("[Error] functions module not available to add a new language.")
                input(T.get("press_enter", "Press Enter to continue..."))
            else:
                functions_module.add_new_language(base_lang="Original", T=T)
                input(T.get("press_enter", "Press Enter to continue..."))
        elif option == "4":
            # alterar raiz de compilation
            new_root = input(T.get("compilation_root_input", "Enter compilation root path: ")).strip()
            if new_root:
                settings["compilation_root"] = new_root
                save_settings(settings, SETTINGS_PATH)
                print(T.get("compilation_root_ok", "Compilation root updated."))
            else:
                print("[Info] No changes made.")
            input(T.get("press_enter", "Press Enter to continue..."))
        elif option.upper() == "V":
            break
        else:
            input(T["invalid"])

def menu(settings: dict, BASE_DIR: str, CONFIG_PATH: str, SETTINGS_PATH: str, TRANSLATIONS: dict, functions):
    T = load_settings(settings, SETTINGS_PATH, TRANSLATIONS, functions, BASE_DIR)

    BOLD = "\033[1m"
    ORANGE = "\033[38;5;208m"
    BLUE = "\033[34m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(f"    {BOLD}{ORANGE}{T['title']}{RESET}")
        print(f"{T['bar']}")

        # Substitui opções separadas de BSPs/WADs por "Compilar jogo"
        # Ordem trocada: 3 = Montar (links), 4 = Configurações
        print(
            f"{BOLD}{ORANGE}1. {RESET}{BOLD}{T['option_compile_all']}{RESET}  "
            f"{BOLD}{ORANGE}2. {RESET}{BOLD}{T.get('option_compile_game')}{RESET}  "
            f"{BOLD}{ORANGE}3. {RESET}{BOLD}{T['option_links']}{RESET}  "
            f"{BOLD}{ORANGE}4. {RESET}{BOLD}{T['option_settings']}{RESET}  "
            f"{BOLD}{RED}V. {RESET}{BOLD}{T['option_exit']}{RESET}"
        )

        print(f"{T['bar_2']}")
        choice = input(build_select_prompt(T, max_number=4)).strip()

        if choice == "1":
            functions.compile_all_wads(CONFIG_PATH, settings, T)
        elif choice == "2":
            groups = functions.load_groups_from_config(CONFIG_PATH)
            if not groups:
                print(f"{RED}{T.get('no_groups_defined', 'No groups defined in groups file.')}{RESET}")
                input()
                continue

            group_list = list(groups.keys())
            print("\n" + T.get("choose_game_group", "Choose the game group:") + "\n")
            print("0. " + T.get("compile_all_groups", "Compile ALL groups"))

            # Usa apenas psd_folder das seções do ini para decidir se o idioma existe
            main_config = functions.read_config_block(CONFIG_PATH)
            lang_folder = settings.get("lang_folder", "")

            for idx, name in enumerate(group_list, start=1):
                exists = False

                # percorre seções do grupo e tenta usar psd_folder
                for section in groups.get(name, []):
                    if section not in main_config:
                        continue
                    sec = main_config[section]
                    
                    # CORREÇÃO APLICADA: Tenta 'psd_folder' primeiro, e depois 'output_qlumpy' como fallback
                    raw = sec.get("psd_folder", "") or sec.get("output_qlumpy", "") or "" 
                    
                    if not raw:
                        continue
                    raw = raw.strip()
                    try:
                        normalized = functions.normalize_path(raw, settings)
                    except Exception:
                        normalized = os.path.abspath(os.path.expanduser(raw))

                    # divide o caminho normalizado em componentes e procura o componente igual ao idioma
                    comps = [c for c in normalized.split(os.sep) if c]
                    for i, comp in enumerate(comps):
                        if comp.lower() == lang_folder.lower():
                            # reconstrói o caminho até o componente do idioma (preservando drive se houver)
                            drive, _ = os.path.splitdrive(normalized)
                            if drive:
                                lang_path = os.path.join(drive + os.sep, *comps[:i+1])
                            else:
                                # se o caminho era absoluto (começa com sep), mantém sep no início
                                if normalized.startswith(os.sep):
                                    lang_path = os.path.join(os.sep, *comps[:i+1])
                                else:
                                    lang_path = os.path.join(*comps[:i+1])

                            if os.path.isdir(lang_path):
                                exists = True
                                break
                    if exists:
                        break

                color = GREEN if exists else RED
                print(f"{idx}. {color}{name}{RESET}")
            print(f"V. {T.get('back_label','Back')}")
            choice2 = input("\n" + T.get("enter_option", "Enter option: ")).strip().upper()
            if choice2 == "V":
                continue
            if choice2 == "0":
                for g in group_list:
                    try:
                        functions.compile_game(CONFIG_PATH, g, settings, T)
                    except Exception as e:
                        print(f"{T.get('error_section','Error compiling group')} {g}: {e}")
            elif choice2.isdigit() and 1 <= int(choice2) <= len(group_list):
                chosen = group_list[int(choice2)-1]
                try:
                    functions.compile_game(CONFIG_PATH, chosen, settings, T)
                except Exception as e:
                    print(f"{T.get('error_section','Error compiling group')} {chosen}: {e}")
            input("\n" + T["completed"])
        elif choice == "3":
            # Montar (links)
            functions.create_links(CONFIG_PATH, settings, T)
            input("\n" + T.get("press_enter", "Press Enter to continue..."))
        elif choice == "4":
            # Configurações
            settings_menu(settings, T, SETTINGS_PATH, BASE_DIR, functions)
            T = load_settings(settings, SETTINGS_PATH, TRANSLATIONS, functions)
        elif choice.lower() == "v":
            print("\n" + T["exiting"])
            break
        else:
            input(T["invalid"])

def start(settings: dict, BASE_DIR: str, CONFIG_PATH: str, SETTINGS_PATH: str, TRANSLATIONS: dict, functions_module):
    menu(settings, BASE_DIR, CONFIG_PATH, SETTINGS_PATH, TRANSLATIONS, functions_module)