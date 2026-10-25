"""Persistence for shared DJ state (SY1): one `dj_state` row per Spotify user
in Supabase, reached through its PostgREST API with the service-role key.

Concurrency is optimistic: every write names the version it was based on, and
the update only applies if the row still has that version. Losing a race
raises Conflict; the client re-applies its change on top of the winner.
"""
import logging
from datetime import datetime, timedelta, timezone

import httpx

from config import SUPABASE_SERVICE_KEY, SUPABASE_URL

log = logging.getLogger(__name__)

# Participants are told the primary "stopped driving" after this much silence,
# and the primary's heartbeat is written at most this often (SY0 decision).
OFFLINE_AFTER = timedelta(seconds=60)
HEARTBEAT_EVERY = timedelta(seconds=15)


class Conflict(Exception):
    """The row changed since the client's version (or already exists)."""


class Unavailable(Exception):
    """Supabase didn't answer or rejected the request."""


def now() -> datetime:
    return datetime.now(timezone.utc)


class DJStore:
    def __init__(self, url: str = SUPABASE_URL, key: str = SUPABASE_SERVICE_KEY):
        self._http = httpx.Client(
            base_url=f'{url}/rest/v1',
            headers={'apikey': key, 'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            timeout=8.0,
        )

    def _call(self, method: str, params: dict, json=None, prefer: str | None = None) -> httpx.Response:
        headers = {'Prefer': prefer} if prefer else {}
        try:
            res = self._http.request(method, '/dj_state', params=params, json=json, headers=headers)
        except httpx.HTTPError as e:
            raise Unavailable(str(e)) from e
        if res.status_code == 409:  # unique violation on insert
            raise Conflict()
        if res.status_code >= 400:
            log.warning('[dj-store] %s -> %s %s', method, res.status_code, res.text[:200])
            raise Unavailable(f'Supabase {res.status_code}')
        return res

    def read(self, user: str) -> dict | None:
        rows = self._call('GET', {'spotify_user_id': f'eq.{user}', 'select': '*'}).json()
        return rows[0] if rows else None

    def create(self, user: str, state: dict, device: str | None, label: str | None) -> dict:
        """First write for a user. The creating device becomes primary (Jam host)."""
        row = {'spotify_user_id': user, 'version': 1, 'state': state,
               'primary_device': device, 'primary_label': label,
               'primary_seen_at': now().isoformat() if device else None}
        return self._call('POST', {}, json=row, prefer='return=representation').json()[0]

    def update(self, user: str, state: dict, expected_version: int) -> dict:
        rows = self._call(
            'PATCH',
            {'spotify_user_id': f'eq.{user}', 'version': f'eq.{expected_version}'},
            json={'state': state, 'version': expected_version + 1, 'updated_at': now().isoformat()},
            prefer='return=representation',
        ).json()
        if not rows:
            raise Conflict()
        return rows[0]

    def claim_primary(self, user: str, device: str, label: str) -> dict | None:
        rows = self._call(
            'PATCH', {'spotify_user_id': f'eq.{user}'},
            json={'primary_device': device, 'primary_label': label, 'primary_seen_at': now().isoformat()},
            prefer='return=representation',
        ).json()
        return rows[0] if rows else None

    def heartbeat(self, user: str, device: str) -> None:
        # Filtered on primary_device so a heartbeat racing a takeover can't
        # overwrite the new primary.
        self._call('PATCH', {'spotify_user_id': f'eq.{user}', 'primary_device': f'eq.{device}'},
                   json={'primary_seen_at': now().isoformat()})


def primary_info(row: dict | None, at: datetime | None = None) -> dict | None:
    if not row or not row.get('primary_device'):
        return None
    seen = row.get('primary_seen_at')
    seen_at = datetime.fromisoformat(seen) if isinstance(seen, str) else seen
    online = bool(seen_at and (at or now()) - seen_at < OFFLINE_AFTER)
    return {'device': row['primary_device'], 'label': row.get('primary_label') or '',
            'seen_at': seen_at.isoformat() if seen_at else None, 'online': online}


def heartbeat_due(row: dict, device: str, at: datetime | None = None) -> bool:
    if row.get('primary_device') != device:
        return False
    seen = row.get('primary_seen_at')
    seen_at = datetime.fromisoformat(seen) if isinstance(seen, str) else seen
    return seen_at is None or (at or now()) - seen_at >= HEARTBEAT_EVERY
