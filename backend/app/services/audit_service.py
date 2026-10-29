import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.models.schemas import AuditEntry
from app.core.security import redact_secret_string

class AuditService:
    def __init__(self):
        self._logs: List[AuditEntry] = []

    def record_event(
        self,
        event_type: str,
        repository: str,
        commit_sha: str,
        details: str,
        actor: str = "System"
    ) -> AuditEntry:
        # Guarantee raw secrets never appear in audit
        clean_details = redact_secret_string(details)
        now = datetime.now(timezone.utc).isoformat()
        
        # Calculate cryptographic integrity hash for tamper-evident logs
        hash_payload = f"{now}:{event_type}:{repository}:{commit_sha}:{clean_details}:{actor}"
        integrity_hash = hashlib.sha256(hash_payload.encode()).hexdigest()

        entry = AuditEntry(
            timestamp=now,
            event_type=event_type,
            repository=repository,
            commit_sha=commit_sha[:8] if commit_sha else "unknown",
            details=clean_details,
            actor=actor,
            integrity_hash=integrity_hash
        )
        self._logs.append(entry)
        return entry

    def get_logs(self) -> List[AuditEntry]:
        return list(self._logs)

# Global in-memory audit service instance
audit_logger = AuditService()

