import subprocess
import time


def debug_message(message: str, color: str, BOLD: str = "\033[1m", RESET: str = "\033[0m"):
    print(f"{BOLD}{color}{message}{RESET}")


def run_with_spinner(cmd: list, message: str = "Processing..."):
    """
    Runs a subprocess hiding stdout/stderr and prints a small spinner while waiting.
    Raises subprocess.CalledProcessError if process returns non-zero.
    """
    spinner = ["|", "/", "-", "\\"]
    if message:
        print(message)
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    i = 0
    try:
        while p.poll() is None:
            print(f"\r{spinner[i % 4]} ", end="", flush=True)
            time.sleep(0.12)
            i += 1
        rc = p.returncode
        print("\r", end="", flush=True)
        if rc != 0:
            raise subprocess.CalledProcessError(rc, cmd)
        return rc
    except KeyboardInterrupt:
        try:
            p.kill()
        except Exception:
            pass
        raise
