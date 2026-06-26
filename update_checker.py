"""
Self-update support for the packaged .exe.
Checks the GitHub Releases API (public repo, no auth needed) for a newer
version, downloads the new .exe, and swaps it in via a small batch script
that runs after this process exits (a running .exe can't overwrite itself).
"""
import json
import os
import subprocess
import sys
import urllib.request

GITHUB_REPO = "shivanshxx/RKE"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
EXE_ASSET_NAME = "RKE_Payroll.exe"


def _parse_version(v):
    v = v.lstrip('vV')
    parts = []
    for p in v.split('.'):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update(current_version, timeout=5):
    """Returns (latest_version, download_url) if a newer release exists, else (None, None)."""
    try:
        req = urllib.request.Request(LATEST_RELEASE_API, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None, None  # offline, rate-limited, or no releases yet — fail silently

    latest_tag = data.get('tag_name', '')
    if not latest_tag:
        return None, None

    if _parse_version(latest_tag) <= _parse_version(current_version):
        return None, None

    download_url = None
    for asset in data.get('assets', []):
        if asset.get('name') == EXE_ASSET_NAME:
            download_url = asset.get('browser_download_url')
            break

    if not download_url:
        return None, None

    return latest_tag, download_url


def download_and_apply_update(download_url, progress_callback=None):
    """
    Downloads the new exe next to the current one, then spawns a batch
    script that (after this process exits) replaces the old exe with the
    new one and relaunches it. Call sys.exit() right after this returns.
    """
    if not getattr(sys, 'frozen', False):
        raise RuntimeError("Self-update only works for the packaged .exe, not when running from source.")

    current_exe = os.path.abspath(sys.executable)
    exe_dir = os.path.dirname(current_exe)
    new_exe = os.path.join(exe_dir, "RKE_Payroll_new.exe")

    with urllib.request.urlopen(download_url, timeout=30) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        downloaded = 0
        with open(new_exe, 'wb') as f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    progress_callback(downloaded, total)

    bat_path = os.path.join(exe_dir, "_rke_update.bat")
    with open(bat_path, 'w') as f:
        f.write(f"""@echo off
ping 127.0.0.1 -n 2 > nul
:retry
del "{current_exe}" 2>nul
if exist "{current_exe}" (
    ping 127.0.0.1 -n 2 > nul
    goto retry
)
move /y "{new_exe}" "{current_exe}" > nul
start "" "{current_exe}"
del "%~f0"
""")
    subprocess.Popen(['cmd', '/c', bat_path], creationflags=subprocess.CREATE_NO_WINDOW,
                      close_fds=True)
