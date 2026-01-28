import os
import logging
from typing import Optional, Dict, Any

try:
    from azure.data.tables import TableServiceClient, TableClient
except ImportError:  # pragma: no cover - handled by tests via mocks
    TableServiceClient = None
    TableClient = None

logger = logging.getLogger(__name__)


class CallStateStore:
    """
    Simple call state store backed by Azure Table Storage.

    Purpose:
    - Persist caller phone `rawId` (e.g. \"4:+123456789\") keyed by call_connection_id
    - Survive Azure Functions scale-out / multiple worker processes
    """

    def __init__(self) -> None:
        conn_str = os.getenv("CALL_STATE_STORAGE_CONN")
        table_name = os.getenv("CALL_STATE_TABLE", "callstate")

        self._enabled = bool(conn_str and TableServiceClient is not None)
        if not self._enabled:
            logger.warning(
                "CallStateStore disabled. Set CALL_STATE_STORAGE_CONN and install azure-data-tables "
                "to enable durable call state (recommended for production)."
            )
            self._table: Optional[TableClient] = None
            return

        try:
            service = TableServiceClient.from_connection_string(conn_str)
            self._table = service.get_table_client(table_name)
            try:
                self._table.create_table()
            except Exception:
                # Table may already exist; that's fine
                pass
            logger.info(f"CallStateStore initialized for table '{table_name}'")
        except Exception as exc:  # pragma: no cover - infrastructure error
            logger.error(f"Failed to initialize CallStateStore: {exc}", exc_info=True)
            self._enabled = False
            self._table = None

    def put_phone(self, call_id: str, phone_raw: str) -> None:
        if not self._enabled or not self._table:
            return
        try:
            entity: Dict[str, Any] = {
                "PartitionKey": "calls",
                "RowKey": call_id,
                "phone_raw": phone_raw,
            }
            self._table.upsert_entity(entity)
            logger.info(f"[CallStateStore] Stored phone_raw for call {call_id}: {phone_raw}")
        except Exception as exc:  # pragma: no cover
            logger.error(f"[CallStateStore] Failed to store phone for {call_id}: {exc}", exc_info=True)

    def get_phone(self, call_id: str) -> Optional[str]:
        if not self._enabled or not self._table:
            return None
        try:
            entity = self._table.get_entity(partition_key="calls", row_key=call_id)
            phone = entity.get("phone_raw")
            logger.info(f"[CallStateStore] Loaded phone_raw for call {call_id}: {phone}")
            return phone
        except Exception:  # pragma: no cover
            # Not found or other error; caller will handle None
            return None

    def delete(self, call_id: str) -> None:
        if not self._enabled or not self._table:
            return
        try:
            self._table.delete_entity(partition_key="calls", row_key=call_id)
        except Exception:  # pragma: no cover
            # OK if already deleted
            pass


# Singleton instance
call_state = CallStateStore()

