import asyncio
import json
import logging

import aiohttp

from .config import settings

log = logging.getLogger(__name__)
GB = 1024**3


class XUIError(Exception):
    pass

class XUI:
    """Минимальный клиент API панели 3x-ui (cookie-сессия, авто-перелогин)."""

    def __init__(self):
        self._base = settings.xui_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
        self._login_lock = asyncio.Lock()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                # unsafe=True нужен, иначе cookie от панели на голом IP не сохраняются
                cookie_jar=aiohttp.CookieJar(unsafe=True),
                connector=aiohttp.TCPConnector(
                    ssl=None if settings.xui_verify_ssl else False
                ),
                timeout=aiohttp.ClientTimeout(total=20),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _login(self):
        async with self._login_lock:
            s = await self._get_session()
            async with s.post(
                f"{self._base}/login",
                data={"username": settings.xui_username, "password": settings.xui_password},
            ) as r:
                body = await r.json(content_type=None)
            if not body.get("success"):
                raise XUIError(f"Не удалось войти в 3x-ui: {body.get('msg')}")

    async def _call(self, method: str, path: str, data: dict | None = None):
        for attempt in (1, 2):
            s = await self._get_session()
            try:
                async with s.request(method, f"{self._base}{path}", data=data) as r:
                    # 3x-ui отдаёт 404 на API-запросы без авторизации
                    if r.status == 404 and attempt == 1:
                        await self._login()
                        continue
                    if r.status != 200:
                        raise XUIError(f"3x-ui вернул HTTP {r.status} для {path}")
                    text = await r.text()
            except aiohttp.ClientError as e:
                raise XUIError(f"Нет связи с 3x-ui: {e}") from e
            try:
                body = json.loads(text)
            except ValueError:
                raise XUIError(f"3x-ui вернул не JSON для {path}: {text[:100]!r}") from None
            if not body.get("success"):
                raise XUIError(f"3x-ui: {body.get('msg')}")
            return body.get("obj")
        raise XUIError("Не удалось авторизоваться в 3x-ui")

    @staticmethod
    def email_for(tg_id: int) -> str:
        return f"tg_{tg_id}"

    def _client_payload(self, tg_id, uuid, sub_id, expiry_ms, total_gb) -> dict:
        client = {
            "id": uuid,
            "flow": settings.xui_flow,
            "email": self.email_for(tg_id),
            "limitIp": 0,
            "totalGB": int(total_gb * GB),  # 0 = безлимит
            "expiryTime": expiry_ms,
            "enable": True,
            "tgId": str(tg_id),
            "subId": sub_id,
            "comment": "",
            "reset": 0,
        }
        return {
            "id": settings.xui_inbound_id,
            "settings": json.dumps({"clients": [client]}),
        }

    async def add_client(self, tg_id, uuid, sub_id, expiry_ms, total_gb=0):
        data = self._client_payload(tg_id, uuid, sub_id, expiry_ms, total_gb)
        await self._call("POST", "/panel/api/inbounds/addClient", data)

    async def update_client(self, tg_id, uuid, sub_id, expiry_ms, total_gb=0):
        data = self._client_payload(tg_id, uuid, sub_id, expiry_ms, total_gb)
        await self._call("POST", f"/panel/api/inbounds/updateClient/{uuid}", data)

    async def get_traffic(self, tg_id: int) -> dict | None:
        """Статистика клиента берётся из inbound'а (clientStats): этот путь стабилен в разных версиях 3x-ui."""
        inbound = await self._call("GET", f"/panel/api/inbounds/get/{settings.xui_inbound_id}")
        email = self.email_for(tg_id)
        for stat in (inbound or {}).get("clientStats") or []:
            if stat.get("email") == email:
                return stat
        return None


xui = XUI()
