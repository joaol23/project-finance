from datetime import date, timedelta

def last_business_day(year: int, month: int) -> date:
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    d = last_day
    while True:
        if d.weekday() < 5:
            if not (d.month == 12 and d.day == 31):
                return d
        d -= timedelta(days=1)

def month_period_bounds(year: int, month: int) -> tuple[date, date]:
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    start_boundary = last_business_day(prev_year, prev_month)
    end_boundary = last_business_day(year, month)
    return start_boundary, end_boundary
