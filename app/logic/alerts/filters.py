from datetime import datetime, timezone

from sqlmodel import select, Session

from db.database import engine
from models.alert_filter import AlertFilter, AlertFilterCreate, AlertFilterUpdate


def get_alert_filters():
    filters = select(AlertFilter).where(AlertFilter.exclude is True)
    with Session(engine) as session:
        filters = session.exec(filters).all()
    return filters

def get_all_alert_filters():
    with Session(engine) as session:
        return session.exec(select(AlertFilter)).all()

def get_alert_filter_by_id(filter_id: int):
    with Session(engine) as session:
        return session.get(AlertFilter, filter_id)

def create_alert_filter_db(alert_filter: AlertFilterCreate):
    with Session(engine) as session:
        new_filter = AlertFilter(**alert_filter.model_dump())
        session.add(new_filter)
        session.commit()
        session.refresh(new_filter)
        return new_filter

def update_alert_filter_db(filter_id: int, alert_filter: AlertFilterUpdate):
    with Session(engine) as session:
        db_filter = session.get(AlertFilter, filter_id)
        if not db_filter:
            return None
        for key, value in alert_filter.model_dump(exclude_unset=True).items():
            setattr(db_filter, key, value)
        db_filter.updated_at = datetime.now(tz=timezone.utc)
        session.add(db_filter)
        session.commit()
        session.refresh(db_filter)
        return db_filter

def delete_alert_filter_db(filter_id: int):
    with Session(engine) as session:
        db_filter = session.get(AlertFilter, filter_id)
        if not db_filter:
            return None
        session.delete(db_filter)
        session.commit()
        return {"ok": True}
