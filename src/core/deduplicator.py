"""Thread-safe time-interval cooldown deduplication engine for BinaryReceptor v3.3.0.

Replaces complex hash-based deduplication with a high-performance, rock-solid
time-interval cooldown gate directly guarding the central scan dispatcher.
"""
from __future__ import annotations

import threading
import time
import urllib.parse


class ScanDeduplicator:
    """Thread-safe time-interval cooldown deduplication engine.

    Prevents double-typing when BinaryEye forwards identical barcodes simultaneously
    over Bluetooth and HTTP or re-transmits unacknowledged packets within cooldown_ms.
    """

    def __init__(self, window_ms: int = 1500, enabled: bool = True) -> None:
        self._lock = threading.Lock()
        self.cooldown_ms = float(window_ms)
        self.enabled = enabled

        self.last_scan_timestamp: float = 0.0
        self.last_scan_text: str = ""
        self.last_scan_source: str = ""
        self.seen_scan_ids: dict[str, float] = {}

        # Running statistics
        self.total_received: int = 0
        self.duplicates_blocked: int = 0

    @property
    def window_ms(self) -> int:
        return int(self.cooldown_ms)

    @window_ms.setter
    def window_ms(self, val: int) -> None:
        self.cooldown_ms = float(val)

    def update_settings(self, window_ms: int, enabled: bool) -> None:
        """Update cooldown duration and toggle state safely."""
        with self._lock:
            self.cooldown_ms = float(max(50, min(60000, window_ms)))
            self.enabled = enabled

    @staticmethod
    def normalize_content(content: str) -> str:
        """Extract canonical normalized barcode text, tolerating URL encoding and CRLF delimiters."""
        if not content:
            return ""
        # Strip trailing/leading CRLF, tabs, spaces
        cleaned = content.strip("\r\n\t ")
        if "%" in cleaned:
            try:
                unquoted = urllib.parse.unquote_plus(cleaned)
                if unquoted:
                    cleaned = unquoted.strip("\r\n\t ")
            except Exception:
                pass
        return cleaned

    def check_and_record(
        self,
        content: str,
        source: str = "HTTP",
        scan_id: str | None = None,
    ) -> tuple[bool, str]:
        """Check if scan is a duplicate within the cooldown time window.

        Returns:
            (is_duplicate, detail_message)
            If is_duplicate is True, the scan is within cooldown and suppressed.
            If False, the scan is accepted and cooldown timestamp is updated.
        """
        now = time.monotonic()
        canonical = self.normalize_content(content)

        with self._lock:
            self.total_received += 1

            if not self.enabled:
                self.last_scan_timestamp = now
                self.last_scan_text = canonical
                self.last_scan_source = source
                return False, f"Accepted from {source} (Deduplication disabled)"

            # 1. Primary Key scanId check for BinaryEye HTTP retries
            clean_scan_id = scan_id.strip() if scan_id else ""
            if clean_scan_id:
                # Prune older than 60s
                cutoff = now - 60.0
                self.seen_scan_ids = {k: v for k, v in self.seen_scan_ids.items() if v >= cutoff}
                if clean_scan_id in self.seen_scan_ids:
                    id_elapsed = (now - self.seen_scan_ids[clean_scan_id]) * 1000.0
                    self.duplicates_blocked += 1
                    return True, (
                        f"[Cooldown Gate] Ignored duplicate scanId '{clean_scan_id}' via {source} "
                        f"(already processed via {self.last_scan_source} {int(id_elapsed)}ms ago)"
                    )

            elapsed_ms = (now - self.last_scan_timestamp) * 1000.0

            # Suppress duplicate if within cooldown window AND:
            # (different transport source for rapid hybrid arrival OR identical barcode text)
            if elapsed_ms < self.cooldown_ms and (source != self.last_scan_source or canonical == self.last_scan_text):
                self.duplicates_blocked += 1
                if clean_scan_id:
                    msg = (
                        f"[Cooldown Gate] Ignored duplicate scanId '{clean_scan_id}' via {source} "
                        f"(already processed via {self.last_scan_source} {int(elapsed_ms)}ms ago)"
                    )
                else:
                    msg = (
                        f"[Cooldown Gate] Suppressed duplicate scan via {source} "
                        f"(already processed via {self.last_scan_source} {int(elapsed_ms)}ms ago, cooldown {int(self.cooldown_ms)}ms)"
                    )
                return True, msg

            # Accepted: update tracker
            self.last_scan_timestamp = now
            self.last_scan_text = canonical
            self.last_scan_source = source
            if clean_scan_id:
                self.seen_scan_ids[clean_scan_id] = now
            return False, f"Accepted from {source}"

    def reset_stats(self) -> None:
        """Reset counters and clear cooldown timestamp."""
        with self._lock:
            self.last_scan_timestamp = 0.0
            self.last_scan_text = ""
            self.last_scan_source = ""
            self.seen_scan_ids.clear()
            self.total_received = 0
            self.duplicates_blocked = 0

    @property
    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "total_received": self.total_received,
                "duplicates_blocked": self.duplicates_blocked,
            }


# Backward-compatible alias
DeduplicationEngine = ScanDeduplicator
