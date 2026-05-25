"""
File-backed auth service for register/login/profile/settings.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from api.common import ServiceError


class AuthService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self._users_file = data_dir / "users.json"
        self._sessions_file = data_dir / "sessions.json"
        self._session_ttl = 24 * 3600
        self._refresh_ttl = 7 * 24 * 3600
        raw_admins = os.getenv("ADMIN_USERNAMES", "admin")
        self._admin_usernames = {name.strip().lower() for name in raw_admins.split(",") if name.strip()}
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._refresh_index: Dict[str, str] = {}
        self._load_sessions()

    def _default_users_payload(self) -> Dict[str, Any]:
        return {"users": [], "next_id": 1}

    def _load_users(self) -> Dict[str, Any]:
        if not self._users_file.exists():
            return self._default_users_payload()
        try:
            payload = json.loads(self._users_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return self._default_users_payload()
            users = payload.get("users")
            next_id = payload.get("next_id")
            if not isinstance(users, list) or not isinstance(next_id, int):
                return self._default_users_payload()
            return payload
        except Exception:
            return self._default_users_payload()

    def _save_users(self, payload: Dict[str, Any]) -> None:
        self._users_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_sessions(self) -> None:
        if not self._sessions_file.exists():
            self._sessions = {}
            self._refresh_index = {}
            return

        try:
            payload = json.loads(self._sessions_file.read_text(encoding="utf-8"))
        except Exception:
            payload = {}

        sessions = payload.get("sessions", {}) if isinstance(payload, dict) else {}
        refresh_index = payload.get("refresh_index", {}) if isinstance(payload, dict) else {}

        self._sessions = sessions if isinstance(sessions, dict) else {}
        self._refresh_index = refresh_index if isinstance(refresh_index, dict) else {}
        self._prune_expired_sessions(persist=False)

    def _save_sessions(self) -> None:
        payload = {
            "sessions": self._sessions,
            "refresh_index": self._refresh_index,
            "updated_at": datetime.now().isoformat(),
        }
        self._sessions_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _norm(value: str) -> str:
        return str(value or "").strip()

    @staticmethod
    def _hash_password(password: str, salt_hex: str) -> str:
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            200000,
        )
        return digest.hex()

    def _resolve_roles(self, row: Dict[str, Any]) -> list[str]:
        roles = row.get("roles")
        if isinstance(roles, list) and roles:
            normalized = sorted({str(role).strip().lower() for role in roles if str(role).strip()})
            if normalized:
                return normalized

        username = str(row.get("username", "")).strip().lower()
        return ["admin"] if username in self._admin_usernames else ["user"]

    def _permissions_for_roles(self, roles: list[str]) -> list[str]:
        permissions = {"read:market", "read:prediction", "write:profile"}
        if "admin" in roles:
            permissions.update({"read:admin", "write:admin", "read:system", "write:system"})
        return sorted(permissions)

    def _public_user(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "created_at": row.get("created_at"),
            "roles": self._resolve_roles(row),
            "profile": row.get("profile", {}),
            "settings": row.get("settings", {}),
        }

    def _remove_session(self, token: str) -> None:
        session = self._sessions.pop(token, None)
        if session:
            refresh_token = session.get("refresh_token")
            if refresh_token:
                self._refresh_index.pop(refresh_token, None)

    def _prune_expired_sessions(self, persist: bool = True) -> None:
        now = time.time()
        expired = []
        for token, session in self._sessions.items():
            if now > float(session.get("refresh_expires_ts", 0)):
                expired.append(token)
                continue
            if now > float(session.get("expires_ts", 0)) and not session.get("refresh_token"):
                expired.append(token)

        for token in expired:
            self._remove_session(token)

        if persist and expired:
            self._save_sessions()

    def _issue_session(self, user: Dict[str, Any], *, previous_token: Optional[str] = None) -> Dict[str, Any]:
        if previous_token:
            self._remove_session(previous_token)

        now = time.time()
        token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(40)
        expires_at = datetime.fromtimestamp(now + self._session_ttl).isoformat()
        refresh_expires_at = datetime.fromtimestamp(now + self._refresh_ttl).isoformat()

        self._sessions[token] = {
            "user_id": int(user["id"]),
            "expires_ts": now + self._session_ttl,
            "refresh_token": refresh_token,
            "refresh_expires_ts": now + self._refresh_ttl,
        }
        self._refresh_index[refresh_token] = token
        self._save_sessions()

        roles = self._resolve_roles(user)
        return {
            "user": self._public_user(user),
            "token": token,
            "refreshToken": refresh_token,
            "expiresAt": expires_at,
            "refreshExpiresAt": refresh_expires_at,
            "roles": roles,
            "permissions": self._permissions_for_roles(roles),
        }

    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        username = self._norm(username)
        email = self._norm(email).lower()
        password = str(password or "")

        if len(username) < 3:
            raise Exception("Username must be at least 3 characters long")
        if "@" not in email or "." not in email:
            raise Exception("Email address is invalid")
        if len(password) < 6:
            raise Exception("Password must be at least 6 characters long")

        with self._lock:
            payload = self._load_users()
            users = payload["users"]
            if any(str(user.get("username", "")).lower() == username.lower() for user in users):
                raise Exception("Username already exists")
            if any(str(user.get("email", "")).lower() == email for user in users):
                raise Exception("Email address is already registered")

            salt = secrets.token_hex(16)
            user = {
                "id": payload["next_id"],
                "username": username,
                "email": email,
                "password_salt": salt,
                "password_hash": self._hash_password(password, salt),
                "created_at": datetime.now().isoformat(),
                "roles": ["admin"] if username.lower() in self._admin_usernames else ["user"],
                "profile": {"phone": "", "company": "", "bio": ""},
                "settings": {"theme": "light", "language": "zh-CN", "notifications": True},
            }
            users.append(user)
            payload["next_id"] = int(payload["next_id"]) + 1
            self._save_users(payload)
            return self._public_user(user)

    def _find_user(self, users: list, login_name: str) -> Optional[Dict[str, Any]]:
        login_lower = self._norm(login_name).lower()
        for user in users:
            username = str(user.get("username", "")).lower()
            email = str(user.get("email", "")).lower()
            if login_lower == username or login_lower == email:
                return user
        return None

    def login(self, username: str, password: str) -> Dict[str, Any]:
        username = self._norm(username)
        password = str(password or "")
        if not username or not password:
            raise Exception("Username and password are required")

        with self._lock:
            self._prune_expired_sessions()
            payload = self._load_users()
            user = self._find_user(payload["users"], username)
            if user is None:
                raise Exception("User does not exist")

            candidate_hash = self._hash_password(password, str(user["password_salt"]))
            if not hmac.compare_digest(candidate_hash, str(user["password_hash"])):
                raise Exception("Username or password is incorrect")

            return self._issue_session(user)

    def refresh_session(self, refresh_token: str) -> Dict[str, Any]:
        refresh_token = self._norm(refresh_token)
        if not refresh_token:
            raise Exception("Refresh token is required")

        with self._lock:
            self._prune_expired_sessions()
            current_token = self._refresh_index.get(refresh_token)
            if not current_token:
                raise Exception("Refresh token is invalid")

            session = self._sessions.get(current_token)
            if not session:
                self._refresh_index.pop(refresh_token, None)
                self._save_sessions()
                raise Exception("Session is no longer available")

            if time.time() > float(session.get("refresh_expires_ts", 0)):
                self._remove_session(current_token)
                self._save_sessions()
                raise Exception("Refresh token has expired")

            user = self._get_user_by_id(int(session["user_id"]))
            if user is None:
                self._remove_session(current_token)
                self._save_sessions()
                raise Exception("User does not exist")

            return self._issue_session(user, previous_token=current_token)

    def logout(self, token: str) -> None:
        token = self._norm(token)
        if not token:
            raise Exception("Access token is required")

        with self._lock:
            self._remove_session(token)
            self._save_sessions()

    def _get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        payload = self._load_users()
        for user in payload["users"]:
            if int(user.get("id", -1)) == int(user_id):
                return user
        return None

    def validate_token(self, token: str) -> Dict[str, Any]:
        token = self._norm(token)
        if not token:
            raise Exception("Access token is required")

        with self._lock:
            self._prune_expired_sessions()
            session = self._sessions.get(token)
            if not session:
                raise Exception("Login session is invalid")
            if time.time() > float(session.get("expires_ts", 0)):
                raise Exception("Login session has expired")

            user = self._get_user_by_id(int(session["user_id"]))
            if user is None:
                self._remove_session(token)
                self._save_sessions()
                raise Exception("User does not exist")
            return self._public_user(user)

    def _ensure_admin(self, token: str) -> Dict[str, Any]:
        user = self.validate_token(token)
        roles = [str(role).lower() for role in (user.get("roles") or [])]
        if "admin" not in roles:
            raise ServiceError("Administrator privileges are required", 403)
        return user

    def verify_admin(self, token: str) -> Dict[str, Any]:
        return self._ensure_admin(token)

    def list_users(self, token: str) -> Dict[str, Any]:
        self._ensure_admin(token)
        payload = self._load_users()
        public_users = [self._public_user(row) for row in payload.get("users", [])]
        return {"total": len(public_users), "users": public_users}

    def get_database_info(self, token: str) -> Dict[str, Any]:
        self._ensure_admin(token)
        data_dir = Path(__file__).parent.parent / "data"
        files = []
        if data_dir.exists():
            for item in sorted(data_dir.glob("*")):
                if item.is_file():
                    stat = item.stat()
                    files.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "size_bytes": stat.st_size,
                            "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )
        return {
            "storage_type": "file-based",
            "data_dir": str(data_dir),
            "file_count": len(files),
            "files": files,
        }

    def update_user_settings(self, token: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        user = self.validate_token(token)
        if not isinstance(settings, dict):
            raise Exception("Settings payload must be an object")

        with self._lock:
            payload = self._load_users()
            target = None
            for row in payload["users"]:
                if int(row.get("id", -1)) == int(user["id"]):
                    target = row
                    break
            if target is None:
                raise Exception("User does not exist")

            existing = target.get("settings", {})
            if not isinstance(existing, dict):
                existing = {}
            existing.update(settings)
            target["settings"] = existing
            self._save_users(payload)
            return self._public_user(target)

    def update_user_profile(self, token: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        user = self.validate_token(token)
        if not isinstance(profile, dict):
            raise Exception("Profile payload must be an object")

        allowed_fields = {"phone", "company", "bio"}

        with self._lock:
            payload = self._load_users()
            target = None
            for row in payload["users"]:
                if int(row.get("id", -1)) == int(user["id"]):
                    target = row
                    break
            if target is None:
                raise Exception("User does not exist")

            existing = target.get("profile", {})
            if not isinstance(existing, dict):
                existing = {}

            for key, value in profile.items():
                if key not in allowed_fields:
                    continue
                existing[key] = str(value or "").strip()

            target["profile"] = existing
            self._save_users(payload)
            return self._public_user(target)


auth_service = AuthService()
