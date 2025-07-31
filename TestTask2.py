import sys
import subprocess
import shutil
import os
import json
import datetime
from pathlib import Path
from urllib.parse import urlparse


def normalize_repo_url(url: str) -> str:
    url = url.strip()
    if not url.endswith('.git'):
        url += '.git'
    return url


def safe_exit(msg: str, code: int = 0):
    print(f"Error: {msg}")
    sys.exit(code)


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc != ""


def main():
    if len(sys.argv) != 4:
        safe_exit("Usage: python script.py <repo_url> <keep_path> <version>", 1)

    repo_url = normalize_repo_url(sys.argv[1])
    keep_path = Path(sys.argv[2])
    version = sys.argv[3]

    if not is_valid_url(repo_url):
        safe_exit("Invalid repository URL format.", 2)

    repo_name = Path(repo_url).stem
    target_dir = Path.cwd() / repo_name

    if target_dir.exists():
        if not (target_dir / '.git').exists():
            safe_exit(f"'{target_dir}' exists but is not a Git repo.", 3)
    else:
        try:
            subprocess.run(["git", "clone", repo_url,
                           str(target_dir)], check=True)
        except subprocess.CalledProcessError:
            safe_exit("Cloning failed. Check URL or network access.", 4)

    keep_full = target_dir / keep_path
    if not keep_full.exists() or not keep_full.is_dir():
        safe_exit(f"Path '{keep_path}' not found in the repository.", 5)

    temp_keep = target_dir / f".keep_temp_{keep_full.name}"
    try:
        shutil.move(str(keep_full), str(temp_keep))
    except Exception:
        safe_exit("Failed to move the target directory.", 6)

    for item in target_dir.iterdir():
        if item.name in {'.git', temp_keep.name}:
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception:
            continue

    final_keep = target_dir / keep_path
    final_keep.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(temp_keep), str(final_keep))
    except Exception:
        safe_exit("Failed to restore target directory.", 7)

    exts = {'.py', '.js', '.sh'}
    files_list = []
    for root, _, files in os.walk(final_keep):
        for f in files:
            if Path(f).suffix in exts:
                rel = Path(root).joinpath(f).relative_to(final_keep)
                files_list.append(str(rel))

    version_data = {
        "name": "hello world",
        "version": version,
        "files": sorted(files_list)
    }

    try:
        with open(final_keep / 'version.json', 'w', encoding='utf-8') as f:
            json.dump(version_data, f, ensure_ascii=False, indent=2)
    except Exception:
        safe_exit("Failed to write version.json.", 8)

    today = datetime.date.today().strftime('%Y%m%d')
    archive_name = f"{final_keep.name}{today}"
    archive_path = target_dir.parent / archive_name
    try:
        shutil.make_archive(str(archive_path), 'zip',
                            root_dir=final_keep.parent, base_dir=final_keep.name)
    except Exception:
        safe_exit("Failed to create archive.", 9)


if __name__ == '__main__':
    main()
