import PyInstaller.__main__
import os
import shutil

# Clean previous build
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

print("Starting build...")

PyInstaller.__main__.run([
    'main.py',
    '--name=MarketAnalysisTool',
    '--windowed',
    '--onedir',
    '--icon=assets/icon.png',
    # Add plugins folder (source, dest)
    '--add-data=plugins:plugins',
    # Add ui folder (source, dest)
    '--add-data=ui:ui',
    # Ensure dependencies are caught
    '--hidden-import=yfinance',
    '--hidden-import=pandas',
    '--hidden-import=plotly',
    '--hidden-import=PyQt6',
    '--clean',
    '--noconfirm'
])

print("Build complete. Check dist/MarketAnalysisTool")
