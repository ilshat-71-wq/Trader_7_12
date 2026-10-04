from io import BytesIO
from zipfile import ZipFile
import struct

from services.moex_weekend_eligibility_service import MoexWeekendEligibilityService


def _dbf(rows):
    fields = [
        ("SECURITYID", 12),
        ("BOARDID", 8),
        ("WEEKENDSES", 1),
    ]
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(length for _, length in fields)
    data = bytearray(header_len + record_len * len(rows) + 1)
    data[0] = 0x03
    data[4:8] = struct.pack("<I", len(rows))
    data[8:10] = struct.pack("<H", header_len)
    data[10:12] = struct.pack("<H", record_len)

    offset = 32
    for name, length in fields:
        data[offset:offset + 11] = name.encode("ascii")[:11].ljust(11, b"\x00")
        data[offset + 16] = length
        offset += 32

    data[header_len - 1] = 0x0D
    cursor = header_len
    for row in rows:
        data[cursor] = 0x20
        cursor += 1
        for name, length in fields:
            value = row[name].encode("cp1251")[:length].ljust(length, b" ")
            data[cursor:cursor + length] = value
            cursor += length
    data[cursor] = 0x1A
    return bytes(data)


def _zip(rows):
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("STOCK_BOARDSECID.DBF", _dbf(rows))
    return payload.getvalue()


def test_parse_zip_uses_official_weekend_board_and_flag():
    payload = _zip([
        {"SECURITYID": "SBER", "BOARDID": "TQBR", "WEEKENDSES": "Y"},
        {"SECURITYID": "GAZP", "BOARDID": "TQBR", "WEEKENDSES": "N"},
        {"SECURITYID": "TEST", "BOARDID": "TQCB", "WEEKENDSES": "Y"},
    ])
    assert MoexWeekendEligibilityService._parse_zip(payload) == {"SBER"}


def test_parse_zip_accepts_weekend_fund_board():
    payload = _zip([
        {"SECURITYID": "FUND", "BOARDID": "TQTF", "WEEKENDSES": "Y"},
    ])
    assert "FUND" in MoexWeekendEligibilityService._parse_zip(payload)


def test_load_returns_none_when_official_moex_mapping_is_unavailable(monkeypatch):
    class Response:
        status_code = 503
        content = b""

    monkeypatch.setattr(
        "services.moex_weekend_eligibility_service.RequestHelper.get",
        lambda *args, **kwargs: Response(),
    )
    MoexWeekendEligibilityService.clear()
    assert MoexWeekendEligibilityService.load() is None
