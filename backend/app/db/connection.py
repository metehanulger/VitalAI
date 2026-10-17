import logging
from typing import Optional, Any
from app.core.config import settings

logger = logging.getLogger("db2_connection")

class DB2ConnectionManager:
    def __init__(self):
        self._conn = None
        self._is_connected = False
        self._use_sqlite_fallback = False

    def get_connection_string(self) -> str:
        conn_str = (
            f"DATABASE={settings.DB2_DATABASE};"
            f"HOSTNAME={settings.DB2_HOSTNAME};"
            f"PORT={settings.DB2_PORT};"
            f"PROTOCOL={settings.DB2_PROTOCOL};"
            f"UID={settings.DB2_UID};"
            f"PWD={settings.DB2_PWD};"
        )
        if settings.DB2_SECURITY:
            conn_str += f"SECURITY={settings.DB2_SECURITY};"
        return conn_str

    def connect(self) -> Optional[Any]:
        try:
            import ibm_db
            conn_str = self.get_connection_string()
            logger.info(f"Connecting to IBM DB2 server: {settings.DB2_HOSTNAME}:{settings.DB2_PORT}...")
            self._conn = ibm_db.connect(conn_str, "", "")
            self._is_connected = True
            logger.info("IBM DB2 connection established successfully.")
            return self._conn
        except Exception as e:
            logger.warning(f"Could not connect to IBM DB2 ({e}). Local cache / SQLite fallback is enabled.")
            self._is_connected = False
            self._use_sqlite_fallback = True
            return None

    def close(self):
        if self._conn and self._is_connected:
            try:
                import ibm_db
                ibm_db.close(self._conn)
            except Exception:
                pass
            self._is_connected = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected

db_manager = DB2ConnectionManager()
