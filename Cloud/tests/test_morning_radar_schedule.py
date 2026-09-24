from datetime import datetime
from zoneinfo import ZoneInfo

from Cloud.morning_radar_service import MorningRadarService


MSK = ZoneInfo("Europe/Moscow")


def test_morning_radar_matches_moex_session_boundary():
    assert [x.strftime("%H:%M") for x in MorningRadarService.SLOTS] == [
        "07:00", "07:30", "08:00", "08:30", "09:00", "09:30", "09:50"
    ]


def test_final_morning_snapshot_is_before_main_session():
    final_slot = MorningRadarService.SLOTS[-1]
    assert final_slot.hour == 9
    assert final_slot.minute == 50

    main_session = datetime(2026, 9, 24, 10, 0, tzinfo=MSK)
    final_dt = datetime.combine(main_session.date(), final_slot, tzinfo=MSK)
    assert final_dt < main_session
