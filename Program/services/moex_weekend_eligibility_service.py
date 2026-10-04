"""Official MOEX weekend-session eligibility for the SPOT universe.

MOEX publishes the current security/board mapping as SL.ZIP. The file contains
the authoritative WeekendSes flag. BCS Trade API instrument metadata does not
expose WEEKENDSESSION, so weekend SPOT admission must not be inferred from BCS.
"""

from __future__ import annotations

from io import BytesIO
from threading import RLock
from time import monotonic
from zipfile import ZipFile

from api.request_helper import RequestHelper


class MoexWeekendEligibilityService:
    """Load real MOEX WeekendSes flags from the official daily mapping file."""

    URL = "https://iss.moex.com/file/stock_boardsecid/SL.ZIP"
    CACHE_SECONDS = 300.0
    TIMEOUT = 8.0
    RETRIES = 1

    _lock = RLock()
    _cached = None
    _cached_at = 0.0

    @classmethod
    def _decode(cls, value: bytes) -> str:
        raw = bytes(value).rstrip(b"\x00 ").strip()
        for encoding in ("cp1251", "utf-8", "latin1"):
            try:
                return raw.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return raw.decode("latin1", errors="replace").strip()

    @classmethod
    def _parse_dbf(cls, payload: bytes) -> list[dict[str, str]]:
        if len(payload) < 32 or payload[0] not in {0x02, 0x03, 0x30, 0x31, 0x43, 0x63, 0x83, 0x8B}:
            raise ValueError("invalid DBF header")

        record_count = int.from_bytes(payload[4:8], "little")
        header_length = int.from_bytes(payload[8:10], "little")
        record_length = int.from_bytes(payload[10:12], "little")
        if header_length < 33 or record_length < 1:
            raise ValueError("invalid DBF dimensions")

        fields = []
        offset = 32
        while offset + 32 <= header_length - 1:
            descriptor = payload[offset:offset + 32]
            if descriptor[0] == 0x0D:
                break
            name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="ignore").strip().upper()
            length = descriptor[16]
            if name and length:
                fields.append((name, length))
            offset += 32

        if not fields:
            raise ValueError("DBF has no fields")

        rows = []
        data_offset = header_length
        for index in range(record_count):
            start = data_offset + index * record_length
            end = start + record_length
            if end > len(payload):
                break
            row = payload[start:end]
            if not row or row[0:1] == b"*":
                continue
            cursor = 1
            record = {}
            for name, length in fields:
                record[name] = cls._decode(row[cursor:cursor + length])
                cursor += length
            rows.append(record)
        return rows

    @classmethod
    def _parse_zip(cls, payload: bytes) -> set[str]:
        with ZipFile(BytesIO(payload)) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".dbf")]
            if not names:
                raise ValueError("SL.ZIP contains no DBF")
            for name in names:
                rows = cls._parse_dbf(archive.read(name))
                if not rows:
                    continue
                fields = set(rows[0])
                if not {"SECURITYID", "BOARDID", "WEEKENDSES"}.issubset(fields):
                    continue
                return {\n                    row["SECURITYID"].strip().upper()\n                    for row in rows\n                    if row.get("WEEKENDSES", "").strip().upper() == "Y"\n                    and row.get("SECTYPE", "").strip().upper() in {"1", "2"}\n                    and row.get("SECURITYID", "").strip()\n                }
        raise ValueError("SL.ZIP DBF has no WeekendSes mapping")

    @classmethod
    def load(cls) -> set[str] | None:
        now = monotonic()
        with cls._lock:
            if cls._cached is not None and now - cls._cached_at < cls.CACHE_SECONDS:
                return set(cls._cached)

        try:
            response = RequestHelper.get(
                cls.URL,
                timeout=cls.TIMEOUT,
                max_retries=cls.RETRIES,
            )
            if response.status_code != 200:
                print("MOEX weekend mapping HTTP:", response.status_code)
                return None
            eligible = cls._parse_zip(response.content)
        except Exception as exc:
            print("MOEX weekend mapping unavailable:", type(exc).__name__)
            return None

        with cls._lock:
            cls._cached = set(eligible)
            cls._cached_at = monotonic()
        print("MOEX weekend-eligible securities:", len(eligible))
        return set(eligible)

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cached = None
            cls._cached_at = 0.0
