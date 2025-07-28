from enum import Enum
from datetime import datetime, timedelta


class TimeUnit(Enum):
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    
    def __repr__(self):
        return self.value

# TimeUnits
TU = TimeUnit


def get_datetime_range(
    start_time: datetime,
    end_time: datetime,
    unit: TimeUnit = TimeUnit.DAYS,
    granularity: int = 1,
) -> list[datetime]:
    time_range = []
    while True:
        if start_time >= end_time:
            time_range.append(end_time)
            break
        time_range.append(start_time)
        start_time += timedelta(**{unit.value: granularity})
    return time_range

def get_pairs_from_range(dt_range: list[datetime]) -> list[tuple[datetime, datetime]]:
    pairs = []
    for i in range(1, len(dt_range)):
        pairs.append((dt_range[i-1], dt_range[i]))
    return pairs

if __name__ == "__main__":
    start_time = datetime(2023, 1, 1, 1, 2, 3, 123)
    end_time = datetime(2023, 1, 10, 1, 2, 3, 343)
    time_range = get_datetime_range(start_time, end_time, TimeUnit.DAYS, 1)
    print(get_pairs_from_range([x for x in time_range]))
