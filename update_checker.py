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


def get_latest_release(timeout=8):
    """
    Fetch the latest published release. Returns a dict with tag, published
    date (DD-MM-YYYY), release notes and the .exe download URL — or None if
    the check could not be completed (offline / rate-limited / no releases).
    """
    try:
        req = urllib.request.Request(LATEST_RELEASE_API, headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None

    tag = data.get('tag_name', '')
    if not tag:
        return None

    published = data.get('published_at', '') or ''
    published_display = ''
    if published:
        try:
            from datetime import datetime
            published_display = datetime.strptime(
                published, '%Y-%m-%dT%H:%M:%SZ').strftime('%d-%m-%Y')
        except ValueError:
            published_display = published[:10]

    download_url = None
    for asset in data.get('assets', []):
        if asset.get('name') == EXE_ASSET_NAME:
            download_url = asset.get('browser_download_url')
            break

    return {
        'tag': tag,
        'version': tag.lstrip('vV'),
        'name': data.get('name', '') or tag,
        'notes': (data.get('body', '') or '').strip(),
        'published': published_display,
        'download_url': download_url,
        'html_url': data.get('html_url', ''),
    }


def is_newer(latest_version, current_version):
    return _parse_version(latest_version) > _parse_version(current_version)


def check_for_update(current_version, timeout=5):
    """Returns (latest_version, download_url) if a newer release exists, else (None, None)."""
    rel = get_latest_release(timeout=timeout)
    if not rel or not rel.get('download_url'):
        return None, None
    if not is_newer(rel['tag'], current_version):
        return None, None
    return rel['tag'], rel['download_url']


class UpdateCancelled(Exception):
    pass


def check_writable():
    """Confirm the new .exe can actually be written next to the current one.
    Checked before downloading so a permission problem is reported straight
    away rather than after a long download."""
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    probe = os.path.join(exe_dir, '_rke_write_test.tmp')
    try:
        with open(probe, 'wb') as f:
            f.write(b'x')
        os.remove(probe)
        return True, exe_dir
    except Exception as ex:
        return False, f"{exe_dir}\n\n{type(ex).__name__}: {ex}"


def download_and_apply_update(download_url, progress_callback=None, should_cancel=None):
    """
    Downloads the new exe next to the current one, verifies it arrived
    complete, then spawns a batch script that (after this process exits)
    replaces the old exe and relaunches it.

    progress_callback(downloaded_bytes, total_bytes) — total is 0 if unknown.
    should_cancel() — return True to abort the download.
    """
    if not getattr(sys, 'frozen', False):
        raise RuntimeError("Self-update only works for the packaged .exe, not when running from source.")

    current_exe = os.path.abspath(sys.executable)
    exe_dir = os.path.dirname(current_exe)
    new_exe = os.path.join(exe_dir, "RKE_Payroll_new.exe")

    ok, detail = check_writable()
    if not ok:
        raise PermissionError(
            "Cannot write the update into the application folder:\n" + detail +
            "\n\nMove RKE_Payroll.exe to a normal folder (for example Desktop or "
            "Documents) and try again, or download the new version manually.")

    req = urllib.request.Request(download_url, headers={'User-Agent': 'RKE-Payroll-Updater'})
    downloaded = 0
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get('Content-Length') or 0)
        if progress_callback:
            progress_callback(0, total)
        with open(new_exe, 'wb') as f:
            while True:
                if should_cancel and should_cancel():
                    raise UpdateCancelled()
                chunk = resp.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)

    # A truncated download must never replace a working installation
    actual = os.path.getsize(new_exe)
    if total and actual != total:
        os.remove(new_exe)
        raise IOError(f"Download incomplete: got {actual:,} of {total:,} bytes. "
                      "Check the internet connection and try again.")
    if actual < 1_000_000:
        os.remove(new_exe)
        raise IOError(f"Downloaded file looks wrong ({actual:,} bytes). Try again later.")

    bat_path = os.path.join(exe_dir, "_rke_update.bat")
    with open(bat_path, 'w') as f:
        f.write(f"""@echo off
rem Wait for the running application to exit, then swap in the new version.
set TRIES=0
:retry
del "{current_exe}" 2>nul
if not exist "{current_exe}" goto replace
set /a TRIES+=1
if %TRIES% GEQ 60 goto failed
ping 127.0.0.1 -n 2 > nul
goto retry

:replace
move /y "{new_exe}" "{current_exe}" > nul
start "" "{current_exe}"
del "%~f0"
exit

:failed
echo Could not replace the old version - it is still running. > "{exe_dir}\\update_failed.txt"
echo The downloaded update is here: {new_exe} >> "{exe_dir}\\update_failed.txt"
exit
""")
    subprocess.Popen(['cmd', '/c', bat_path], creationflags=subprocess.CREATE_NO_WINDOW,
                      close_fds=True)
