import json
import os
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import current_app

from .version import APP_NAME, APP_VERSION


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
    }


def _default_status():
    return {
        'available': False,
        'required': False,
        'current_version': APP_VERSION,
        'latest_version': None,
        'download_url': None,
        'notes': [],
    }


def get_update_status(force=False):
    app = current_app._get_current_object()
    cache = app.extensions.setdefault('wor_update_status', {
        'checked_at': 0,
        'result': _default_status(),
    })
    now = time.time()
    ttl = int(app.config.get('UPDATE_CHECK_INTERVAL', 0) or 0)

    if not force and cache['checked_at'] and ttl > 0 and now - cache['checked_at'] < ttl:
        return cache['result']

    result = _default_status()
    try:
        raw_manifest = _read_manifest_bytes(app)
        if raw_manifest:
            manifest = json.loads(raw_manifest.decode('utf-8'))
            result = _build_status_from_manifest(manifest)
    except (json.JSONDecodeError, OSError, URLError, ValueError):
        result = _default_status()

    cache['checked_at'] = now
    cache['result'] = result
    return result
