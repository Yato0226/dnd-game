# dnd_ai_game/src/utils/system_utils.py
import sys
import subprocess
import time

def is_ollama_running():
    """Checks if the Ollama process is running."""
    try:
        if sys.platform == "win32":
            command = ["tasklist"]
            process_name = "ollama.exe"
        else:  # macOS and Linux
            command = ["pgrep", "-f", "ollama"]
            process_name = "ollama"

        result = subprocess.run(command, capture_output=True, text=True, check=True)

        if sys.platform == "win32":
            return process_name in result.stdout
        else:
            return result.stdout.strip() != ""  # pgrep returns PIDs

    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    except Exception as e:
        print(f"An unexpected error occurred while checking for Ollama: {e}")
        return False

def start_ollama():
    """Starts the Ollama application in the background."""
    print("Ollama is not running. Attempting to start it...")
    try:
        if sys.platform == "win32":
            subprocess.Popen(["start", "/b", "ollama", "serve"], shell=True)
        else:  # macOS and Linux
            subprocess.Popen(["ollama", "serve"])

        print("Ollama started. Please wait a few seconds for it to initialize.")
        time.sleep(5)  # Give Ollama time to start up
        return True
    except FileNotFoundError:
        print("\nCRITICAL ERROR: 'ollama' command not found.")
        print("Please ensure Ollama is installed and its location is in your system's PATH.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while starting Ollama: {e}")
        return False

def stop_ollama():
    """Stops the Ollama process."""
    if sys.platform != "win32":
        print("Stopping Ollama is currently only supported on Windows.")
        return
    print("Attempting to stop the Ollama process...")
    try:
        result = subprocess.run(["taskkill", "/IM", "ollama.exe", "/F"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Ollama process stopped successfully.")
        else:
            # Code 128 means 'process not found', which is also a success in this context
            if "not found" in result.stderr.lower():
                 print("Ollama process was not running.")
            else:
                print(f"Could not stop Ollama. Error: {result.stderr}")
    except FileNotFoundError:
        print("taskkill command not found. Cannot stop Ollama.")
    except Exception as e:
        print(f"An unexpected error occurred while stopping Ollama: {e}")
