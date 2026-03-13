import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from flask import current_app

from .version import APP_NAME, APP_VERSION


class UpdateError(RuntimeError):
    """Raised when an update is available but cannot be installed safely."""


def auto_update_supported():
    return bool(
        getattr(sys, 'frozen', False)
        and os.name == 'nt'
        and sys.executable.lower().endswith('.exe')
    )


def _parse_version(version):
    parts = []
    for part in str(version or '').strip().lstrip('v').split('.'):
        digits = ''.join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _is_newer(remote_version, local_version=APP_VERSION):
    return _parse_version(remote_version) > _parse_version(local_version)


def _is_required(min_supported_version, local_version=APP_VERSION):
    if not min_supported_version:
        return False
    return _parse_version(local_version) < _parse_version(min_supported_version)


def _read_manifest_bytes(app):
    manifest_url = app.config.get('UPDATE_MANIFEST_URL', '').strip()
    if manifest_url:
        try:
            request = Request(
                manifest_url,
                headers={'User-Agent': f'{APP_NAME}/{APP_VERSION}'}
            )
            with urlopen(request, timeout=3) as response:
                return response.read()
        except (OSError, URLError, ValueError):
            pass

    manifest_path = app.config.get('UPDATE_MANIFEST_PATH', '').strip()
    if manifest_path and os.path.exists(manifest_path):
        with open(manifest_path, 'rb') as f:
            return f.read()

    bundled_manifest_path = app.config.get('UPDATE_MANIFEST_BUNDLED_PATH', '').strip()
    if bundled_manifest_path and os.path.exists(bundled_manifest_path):
        with open(bundled_manifest_path, 'rb') as f:
            return f.read()

    return None


def _build_status_from_manifest(manifest):
    latest_version = str(manifest.get('version', '')).strip()
    if not latest_version:
        return _default_status()

    platform_info = manifest.get('windows') or {}
    notes = manifest.get('notes') or []
    if isinstance(notes, str):
        notes = [notes]

    return {
        'available': _is_newer(latest_version),
        'required': _is_required(manifest.get('min_supported_version')),
        'current_version': APP_VERSION,
        'latest_version': latest_version,
        'download_url': platform_info.get('url') or manifest.get('download_url'),
        'notes': [str(note) for note in notes if str(note).strip()],
        'auto_update_supported': auto_update_supported(),
    }


def _default_status():
    return {
        'available': False,
        'required': False,
        'current_version': APP_VERSION,
        'latest_version': None,
        'download_url': None,
        'notes': [],
        'auto_update_supported': auto_update_supported(),
    }


def get_update_status(force=False):
    app = current_app._get_current_object()
    cache = app.extensions.setdefault('wor_update_status', {
        'checked_at': 0,
        'result': _default_status(),
    })

    # Check once per app process. A restart triggers a fresh remote check.
    if not force and cache['checked_at']:
        return cache['result']

    result = _default_status()
    try:
        raw_manifest = _read_manifest_bytes(app)
        if raw_manifest:
            manifest = json.loads(raw_manifest.decode('utf-8'))
            result = _build_status_from_manifest(manifest)
    except (json.JSONDecodeError, OSError, URLError, ValueError):
        result = _default_status()

    cache['checked_at'] = time.time()
    cache['result'] = result
    return result


def _build_manifest_bytes(status):
    payload = {
        'version': status.get('latest_version') or status.get('current_version'),
        'min_supported_version': status.get('current_version'),
        'notes': status.get('notes') or [],
        'windows': {
            'url': status.get('download_url'),
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8')


def _ensure_install_dir_writable(install_dir):
    probe_path = os.path.join(install_dir, '.__wor_write_probe__')
    try:
        with open(probe_path, 'w', encoding='utf-8') as f:
            f.write('ok')
    except OSError as exc:
        raise UpdateError(
            'De update kan niet worden geïnstalleerd omdat deze map niet schrijfbaar is.'
        ) from exc
    finally:
        try:
            os.remove(probe_path)
        except OSError:
            pass


def _download_release_asset(download_url, work_dir):
    request = Request(
        download_url,
        headers={'User-Agent': f'{APP_NAME}/{APP_VERSION}'}
    )
    try:
        with urlopen(request, timeout=30) as response:
            final_url = response.geturl() or download_url
            filename = unquote(os.path.basename(urlparse(final_url).path)) or 'wor-update'
            asset_path = os.path.join(work_dir, filename)
            with open(asset_path, 'wb') as f:
                shutil.copyfileobj(response, f)
            return asset_path
    except (OSError, URLError, ValueError) as exc:
        raise UpdateError('Het downloaden van de update is mislukt.') from exc


def _extract_release_asset(asset_path, work_dir):
    lower_path = asset_path.lower()
    if lower_path.endswith('.exe'):
        return asset_path

    if lower_path.endswith('.zip'):
        extract_dir = os.path.join(work_dir, 'unzipped')
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(asset_path) as archive:
                archive.extractall(extract_dir)
        except (OSError, zipfile.BadZipFile) as exc:
            raise UpdateError('Het updatebestand kon niet worden uitgepakt.') from exc
        return extract_dir

    raise UpdateError('Het updatebestand moet een .zip of .exe zijn.')


def _find_staged_executable(asset_root):
    preferred_name = os.path.basename(sys.executable).lower()

    if os.path.isfile(asset_root):
        if asset_root.lower().endswith('.exe'):
            return asset_root
        raise UpdateError('Er is geen uitvoerbaar updatebestand gevonden.')

    candidates = []
    for root, _, files in os.walk(asset_root):
        for filename in files:
            if not filename.lower().endswith('.exe'):
                continue
            full_path = os.path.join(root, filename)
            if filename.lower() == preferred_name:
                return full_path
            candidates.append(full_path)

    if not candidates:
        raise UpdateError('Er is geen uitvoerbaar updatebestand gevonden.')

    candidates.sort(key=lambda path: (0 if APP_NAME.lower() in os.path.basename(path).lower() else 1, len(path)))
    return candidates[0]


def _write_manifest_file(app, status, work_dir):
    manifest_bytes = _read_manifest_bytes(app)
    if manifest_bytes:
        try:
            manifest = json.loads(manifest_bytes.decode('utf-8'))
            manifest_version = str(manifest.get('version', '')).strip()
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            manifest_version = ''
        if manifest_version != str(status.get('latest_version') or '').strip():
            manifest_bytes = None

    manifest_bytes = manifest_bytes or _build_manifest_bytes(status)
    manifest_path = os.path.join(work_dir, 'latest.json')
    with open(manifest_path, 'wb') as f:
        f.write(manifest_bytes)
    return manifest_path


def _ps_literal(value):
    return str(value).replace("'", "''")


def _write_update_script(pid, staged_exe, staged_manifest, target_exe, target_manifest, work_dir):
    script_path = os.path.join(work_dir, 'apply_update.ps1')
    script = f"""$ErrorActionPreference = 'Stop'
$parentPid = {pid}
$stagedExe = '{_ps_literal(staged_exe)}'
$stagedManifest = '{_ps_literal(staged_manifest)}'
$targetExe = '{_ps_literal(target_exe)}'
$targetManifest = '{_ps_literal(target_manifest)}'
$logPath = Join-Path $env:TEMP 'wor-update-error.log'

try {{
    while (Get-Process -Id $parentPid -ErrorAction SilentlyContinue) {{
        Start-Sleep -Milliseconds 500
    }}

    Copy-Item -LiteralPath $stagedExe -Destination $targetExe -Force
    Copy-Item -LiteralPath $stagedManifest -Destination $targetManifest -Force
}}
catch {{
    $_ | Out-File -LiteralPath $logPath -Encoding utf8
}}

Start-Process -FilePath $targetExe
"""
    with open(script_path, 'w', encoding='utf-8-sig') as f:
        f.write(script)
    return script_path


def _launch_update_script(script_path):
    creationflags = 0
    for flag_name in ('DETACHED_PROCESS', 'CREATE_NEW_PROCESS_GROUP', 'CREATE_NO_WINDOW'):
        creationflags |= getattr(subprocess, flag_name, 0)

    try:
        subprocess.Popen(
            [
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                '-File', script_path,
            ],
            close_fds=True,
            creationflags=creationflags,
        )
    except OSError as exc:
        raise UpdateError('De update kon niet worden gestart.') from exc


def start_self_update(force=False):
    app = current_app._get_current_object()
    status = get_update_status(force=force)

    if not auto_update_supported():
        raise UpdateError('Automatisch bijwerken is alleen beschikbaar in de Windows-app.')

    if not (status['available'] or status['required']):
        raise UpdateError('Er is momenteel geen nieuwe update beschikbaar.')

    download_url = (status.get('download_url') or '').strip()
    if not download_url:
        raise UpdateError('De update is gevonden, maar de downloadlink ontbreekt in latest.json.')

    install_dir = os.path.dirname(sys.executable)
    _ensure_install_dir_writable(install_dir)

    work_dir = tempfile.mkdtemp(prefix='wor-update-')
    asset_path = _download_release_asset(download_url, work_dir)
    asset_root = _extract_release_asset(asset_path, work_dir)
    staged_exe = _find_staged_executable(asset_root)
    staged_manifest = _write_manifest_file(app, status, work_dir)
    target_manifest = os.path.join(install_dir, 'latest.json')
    script_path = _write_update_script(
        pid=os.getpid(),
        staged_exe=staged_exe,
        staged_manifest=staged_manifest,
        target_exe=sys.executable,
        target_manifest=target_manifest,
        work_dir=work_dir,
    )
    _launch_update_script(script_path)

    return {
        'current_version': status['current_version'],
        'latest_version': status['latest_version'],
    }
