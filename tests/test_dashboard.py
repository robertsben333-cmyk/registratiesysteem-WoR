from datetime import date
from app.models import get_periode_range, SIGNALERING_ACHTERUITGANG_DREMPEL


def test_get_periode_range_alles():
    start, end = get_periode_range('alles')
    assert start is None
    assert end is None


def test_get_periode_range_jaar():
    start, end = get_periode_range('jaar')
    today = date.today()
    assert start == date(today.year, 1, 1)
    assert end == date(today.year, 12, 31)


def test_get_periode_range_kwartaal():
    start, end = get_periode_range('kwartaal')
    today = date.today()
    q = (today.month - 1) // 3
    assert start.month == q * 3 + 1
    assert start.day == 1
    assert start.year == today.year
    assert end.year == today.year
    assert end >= today  # end is always in the future or today within same quarter


def test_signalering_drempel_is_minus_one():
    assert SIGNALERING_ACHTERUITGANG_DREMPEL == -1.0
