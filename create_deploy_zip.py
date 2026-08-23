import os
import zipfile

PROJECT_DIR = r"c:\Users\bosan\projects\my-vibe-app\stock_bot_project"
ZIP_PATH = os.path.join(PROJECT_DIR, "stock_bot_deploy.zip")

include_dirs = ["core", "kr_bot", "us_bot"]
include_files = [
    "interactive_bot.py",
    "webhook_server.py",
    "requirements.txt",
    "Dockerfile",
    ".dockerignore",
    "watchlist.json",
]

with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
    # Add root files
    for fname in include_files:
        fpath = os.path.join(PROJECT_DIR, fname)
        if os.path.exists(fpath):
            zf.write(fpath, arcname=fname)
            print(f"Added file: {fname}")

    # Add directories
    for dname in include_dirs:
        dpath = os.path.join(PROJECT_DIR, dname)
        for root, dirs, files in os.walk(dpath):
            for file in files:
                if file.endswith((".py", ".json", ".txt", ".md")):
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, PROJECT_DIR)
                    zf.write(full_p, arcname=rel_p)
                    print(f"Added: {rel_p}")

print(f"\n✅ Created deployment package: {ZIP_PATH}")
print(f"File size: {os.path.getsize(ZIP_PATH):,} bytes")
