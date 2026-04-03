import os
import subprocess
import platform
import shutil

def run_command(cmd, shell=False):
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        result = subprocess.run(cmd, shell=shell, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr}")
        return None

def detect_hardware():
    system = platform.system()
    machine = platform.machine()
    
    print(f"Detecting hardware on {system} ({machine})...")
    
    if system == "Darwin":
        if "arm" in machine.lower():
            return "mac"
        return "cpu"
    
    # Check for NVIDIA
    if shutil.which("nvidia-smi"):
        print("NVIDIA GPU detected.")
        return "nvidia"
    
    # Check for AMD (Linux/Windows)
    if system == "Linux" and os.path.exists("/dev/kfd"):
        print("AMD GPU detected (Linux).")
        return "amd"
    
    # Simple check for AMD on Windows (rocminfo is rare, but we can check via wmic)
    if system == "Windows":
        wmic_out = run_command(["wmic", "path", "win32_VideoController", "get", "name"])
        if wmic_out and "AMD" in wmic_out.upper():
            print("AMD GPU detected (Windows).")
            return "amd"
            
    print("No specialized hardware detected, falling back to CPU.")
    return "cpu"

def main():
    target = detect_hardware()
    print(f"Target selected: {target}")
    
    # Installation commands using uv
    # Note: For NVIDIA, we might need specific index URLs
    cmd_base = ["uv", "sync", "--group", target]
    
    if target == "nvidia":
        print("Attempting to install Torch with CUDA 12.4 support...")
        # uv can use --extra-index-url from environment or config
        os.environ["UV_EXTRA_INDEX_URL"] = "https://download.pytorch.org/whl/cu124"
    elif target == "amd":
        print("Attempting to install Torch with ROCm support...")
        os.environ["UV_EXTRA_INDEX_URL"] = "https://download.pytorch.org/whl/rocm6.1"
    
    try:
        run_command(cmd_base)
        print(f"Successfully configured RustyMiroSquid for {target}!")
    except Exception as e:
        print(f"Installation failed: {e}")
        print("Suggestion: Try manual installation of torch for your specific hardware.")

if __name__ == "__main__":
    main()
