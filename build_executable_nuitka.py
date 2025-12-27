
import os
import shutil
import subprocess
import sys

def build():
    # Clean previous build
    if os.path.exists('build'):
        shutil.rmtree('build')
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    
    print("Starting Nuitka build...")
    
    # Nuitka command
    # Using python -m nuitka to ensure we use the installed module in current env
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--macos-create-app-bundle",
        "--enable-plugin=pyside6",
        "--include-data-dir=plugins=plugins",
        "--include-data-dir=ui=ui",
        "--include-data-dir=assets=assets",
        "--output-dir=dist",
        "--main=main.py",
        "--product-name=MarketAnalysisTool",
        "--macos-app-icon=assets/icon.png",
        "--macos-app-icon=assets/icon.png",
        "--include-package=plotly",
        "--user-package-configuration-file=nuitka-config.yaml",
        "--assume-yes-for-downloads"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("Build complete. Check dist/MarketAnalysisTool.app")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build()
