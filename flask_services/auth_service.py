"""
Lightweight auth service for register/login/profile/settings.
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


class AuthService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._users_file = Path(__file__).parent.parent / "data" / "users.json"
        self._users_file.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._refresh_index: Dict[str, str] = {}
        self._session_ttl = 24 * 3600
        self._refresh_ttl = 7 * 24 * 3600
        raw_admins = os.getenv("ADMIN_USERNAMES", "admin")
        self._admin_usernames = {name.strip().lower() for name in raw_admins.split(",") if name.strip()}

    def _load_users(self) -> Dict[str, Any]:
        if not self._users_file.exists():
            return {"users": [], "next_id": 1}
        try:
            payload = json.loads(self._users_file.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return {"users": [], "next_id": 1}
            users = payload.get("users")
            next_id = payload.get("next_id")
            if not isinstance(users, list) or not isinstance(next_id, int):
                return {"users": [], "next_id": 1}
            return payload
        except Exception:
            return {"users": [], "next_id": 1}

    def _save_users(self, payload: Dict[str, Any]) -> None:
        self._users_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

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

    def _public_user(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "created_at": row.get("created_at"),
            "roles": row.get("roles", ["user"]),
            "profile": row.get("profile", {}),
            "settings": row.get("settings", {}),
        }

    def _prune_expired_sessions(self) -> None:
        now = time.time()
        expired = [
            token for token, session in self._sessions.items() if now > float(session.get("expires_ts", 0))
        ]
        for token in expired:
            refresh_token = self._sessions.get(token, {}).get("refresh_token")
            self._sessions.pop(token, None)
            if refresh_token:
                self._refresh_index.pop(refresh_token, None)

    def register(self, username: str, email: str, password: str) -> Dict[str, Any]:
        username = self._norm(username)
        email = self._norm(email).lower()
        password = str(password or "")

        if len(username) < 3:
            raise Exception("用户名至少 3 个字符")
        if "@" not in email or "." not in email:
            raise Exception("邮箱格式不正确")
        if len(password) < 6:
            raise Exception("密码至少 6 位")

        with self._lock:
            payload = self._load_users()
            users = payload["users"]
            if any(str(user.get("username", "")).lower() == username.lower() for user in users):
                raise Exception("用户名已存在")
            if any(str(user.get("email", "")).lower() == email for user in users):
                raise Exception("邮箱已被注册")

            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            user = {
                "id": payload["next_id"],
                "username": username,
                "email": email,
                "password_salt": salt,
                "password_hash": password_hash,
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
            raise Exception("用户名和密码不能为空")

        with self._lock:
            self._prune_expired_sessions()
            payload = self._load_users()
            user = self._find_user(payload["users"], username)
            if user is None:
                raise Exception("用户不存在")

            candidate_hash = self._hash_password(password, str(user["password_salt"]))
            if not hmac.compare_digest(candidate_hash, str(user["password_hash"])):
                raise Exception("用户名或密码错误")

            now = time.time()
            token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(40)
            expires_at = datetime.fromtimestamp(now + self._session_ttl).isoformat()
            refresh_expires_at = datetime.fromtimestamp(now + self._refresh_ttl).isoformat()

            self._sessions[token] = {
                "user_id": user["id"],
                "expires_ts": now + self._session_ttl,
                "refresh_token": refresh_token,
                "refresh_expires_ts": now + self._refresh_ttl,
            }
            self._refresh_index[refresh_token] = token

            return {
                "user": self._public_user(user),
                "token": token,
                "refreshToken": refresh_token,
                "expiresAt": expires_at,
                "refreshExpiresAt": refresh_expires_at,
                "roles": user.get("roles", ["user"]),
                "permissions": ["read:market", "read:prediction", "write:profile"],
            }

    def _get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        payload = self._load_users()
        for user in payload["users"]:
            if int(user.get("id", -1)) == int(user_id):
                return user
        return None

    def validate_token(self, token: str) -> Dict[str, Any]:
        token = self._norm(token)
        if not token:
            raise Exception("缺少访问令牌")
        session = self._sessions.get(token)
        if not session:
            raise Exception("登录状态无效，请重新登录")
        if time.time() > float(session.get("expires_ts", 0)):
            refresh_token = session.get("refresh_token")
            self._sessions.pop(token, None)
            if refresh_token:
                self._refresh_index.pop(refresh_token, None)
            raise Exception("登录已过期，请重新登录")

        user = self._get_user_by_id(int(session["user_id"]))
        if user is None:
            raise Exception("用户不存在")
        return self._public_user(user)

    def _ensure_admin(self, token: str) -> Dict[str, Any]:
        user = self.validate_token(token)
        roles = [str(role).lower() for role in (user.get("roles") or [])]
        if "admin" not in roles:
            raise Exception("需要管理员权限")
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
            raise Exception("设置参数格式错误")

        with self._lock:
            payload = self._load_users()
            target = None
            for row in payload["users"]:
                if int(row.get("id", -1)) == int(user["id"]):
                    target = row
                    break
            if target is None:
                raise Exception("用户不存在")

            existing = target.get("settings", {})
            if not isinstance(existing, dict):
                existing = {}
            existing.update(settings)
            target["settings"] = existing
            self._save_users(payload)
            return self._public_user(target)


auth_service = AuthService()
