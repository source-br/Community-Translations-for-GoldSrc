import os
import shutil
import ctypes

# Assumindo que path_utils está definido corretamente
from .path_utils import normalize_path, read_config_block

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_links(config_path: str, settings: dict, T: dict):
    """
    Lê o arquivo de configuração e o 'links.ini' para criar links simbólicos.
    Corrigido para lidar com permissões e tipos de arquivos no Windows 11.
    """
    print("--- Iniciando Criação de Links Simbólicos ---")
    
    # Validação de privilégios (Essencial para Windows)
    if not is_admin():
        print("⚠️  AVISO: O script não está rodando como Administrador.")
        print("No Windows, a criação de symlinks geralmente requer privilégios elevados.")

    try:
        main_config = read_config_block(config_path)
    except Exception as e:
        print(f"Erro ao ler a configuração principal em {config_path}: {e}")
        return

    # 1. Encontra o caminho do links.ini
    links_ini = None
    if "global" in main_config and main_config["global"].get("links_ini"):
        links_ini = normalize_path(main_config["global"]["links_ini"], settings)
    else:
        links_ini = os.path.join(os.path.dirname(os.path.abspath(config_path)), "links.ini")

    if not os.path.exists(links_ini):
        print(f"Erro: Arquivo links.ini não encontrado: {links_ini}")
        return

    try:
        links_config = read_config_block(links_ini)
    except Exception as e:
        print(f"Erro ao ler links.ini em {links_ini}: {e}")
        return
    
    created = 0
    ignored = 0

    for section in links_config.sections():
        if not (links_config.has_option(section, "origem_folder") and links_config.has_option(section, "destino_folder")):
            continue

        try:
            source = normalize_path(links_config[section]["origem_folder"], settings)
            destinos_raw = links_config[section]["destino_folder"]
            destinos = [normalize_path(d.strip(), settings) for d in destinos_raw.split(",")]

            if not os.path.exists(source):
                print(f"Ignorado ({section}): Origem inexistente: {source}")
                ignored += 1
                continue

            is_source_dir = os.path.isdir(source)
            
            for destination in destinos:
                print(f"Processando: '{source}' -> '{destination}'")

                # C. Limpeza Robusta para Windows
                if os.path.lexists(destination):
                    try:
                        # No Windows, se o destino for um link para diretório, 
                        # os.remove() ou os.rmdir() devem ser usados dependendo da versão.
                        # os.path.islink + os.path.isdir identifica um symlink de pasta.
                        if os.path.isdir(destination):
                            if os.path.islink(destination):
                                os.rmdir(destination) # Remove o link da pasta (não o conteúdo)
                            else:
                                shutil.rmtree(destination) # Remove pasta real
                        else:
                            os.remove(destination) # Remove arquivo ou link de arquivo
                    except Exception as e:
                        print(f"  ❌ Erro de Remoção: {e}")
                        ignored += 1
                        continue

                # D. Criação com Verificação de Pasta Pai
                try:
                    dest_parent = os.path.dirname(destination)
                    if not os.path.exists(dest_parent):
                        os.makedirs(dest_parent, exist_ok=True)

                    os.symlink(source, destination, target_is_directory=is_source_dir)
                    created += 1
                    print(f"  ✅ Sucesso: {destination}")
                except OSError as e:
                    print(f"  ❌ Erro de Sistema: {e.strerror}")
                    if e.winerror == 1314:
                        print("     Causa: Falta de privilégio (A Privilege Held by the Client).")
                    ignored += 1

        except Exception as e:
            print(f"  ❌ Erro Inesperado na seção '{section}': {e}")
            ignored += 1

    print(f"\n--- Fim: {created} criados, {ignored} ignorados ---")