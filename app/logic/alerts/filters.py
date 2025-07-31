from collections import defaultdict
from datetime import datetime, timezone

import pandas as pd
from sqlmodel import select, Session

from helpers import logger
from db.database import engine
from helpers.agy_utils import get_id_type, default_idtype_column_map
from models.alert_filter import (
    AlertFilter,
    AlertFilterCreate,
    AlertFilterUpdate,
    IdType,
)


def filter_df_by_alert_filters(
    df: pd.DataFrame,
    filters: list[AlertFilter] | None = None,
    idtype_column_map: dict[IdType, str] = default_idtype_column_map,
) -> pd.DataFrame:
    # If no filters are provided, use the excluded filters
    if not filters:
        filters = get_excluded_alert_filters()

    # If no filters are found, return the dataframe
    if not filters:
        return df

    # Create a map of column names to entity IDs
    column_values_map = defaultdict(list)
    for filter in filters:
        if filter.id_type not in idtype_column_map.keys():
            continue
        column_values_map[idtype_column_map[filter.id_type]].append(filter.entity_id)

    # For each column, remove any rows where the entity ID is in the exclusion list
    for column, exclusions in column_values_map.items():
        df = df[~df[column].isin(exclusions)]

    return df


def get_excluded_alert_filters():
    filters = select(AlertFilter).where(AlertFilter.exclude)
    with Session(engine) as session:
        filters = session.exec(filters).all()
    return filters


def get_all_alert_filters():
    with Session(engine) as session:
        return session.exec(select(AlertFilter)).all()


def get_alert_filter_by_id(filter_id: int):
    with Session(engine) as session:
        return session.get(AlertFilter, filter_id)


def get_alert_filter_by_entity_id(entity_id: str):
    with Session(engine) as session:
        return session.exec(
            select(AlertFilter).where(AlertFilter.entity_id == entity_id)
        ).first()


def create_alert_filter_db(alert_filter: AlertFilterCreate):
    try:
        with Session(engine) as session:
            new_filter = AlertFilter(**alert_filter.model_dump())
            session.add(new_filter)
            session.commit()
            session.refresh(new_filter)
            return new_filter
    except Exception as err:
        if "duplicate entry" in str(err).lower():
            return f"Alert filter for {alert_filter.entity_id!r} already exists"
        logger.error("Error creating alert filter:", err)
        return "Failed to create alert filter"


def _update_alert_filter_generic(column, value, alert_filter: AlertFilterUpdate):
    with Session(engine) as session:
        db_filter = session.exec(select(AlertFilter).where(column == value)).first()
        if not db_filter:
            return None
        for key, value in alert_filter.model_dump(exclude_unset=True).items():
            setattr(db_filter, key, value)
        db_filter.updated_at = datetime.now(tz=timezone.utc)
        session.add(db_filter)
        session.commit()
        session.refresh(db_filter)
        return db_filter


def update_alert_filter_by_id(filter_id: int, alert_filter: AlertFilterUpdate):
    return _update_alert_filter_generic(AlertFilter.id, filter_id, alert_filter)


def update_alert_filter_by_entity_id(entity_id: str, alert_filter: AlertFilterUpdate):
    return _update_alert_filter_generic(AlertFilter.entity_id, entity_id, alert_filter)


def _delete_alert_filter_generic(column, value):
    with Session(engine) as session:
        db_filter = session.exec(select(AlertFilter).where(column == value)).first()
        if not db_filter:
            return False
        session.delete(db_filter)
        session.commit()
        return True


def delete_alert_filter_by_id(filter_id: int):
    return _delete_alert_filter_generic(AlertFilter.id, filter_id)


def delete_alert_filter_by_entity_id(entity_id: str):
    return _delete_alert_filter_generic(AlertFilter.entity_id, entity_id)


def toggle_entity_alert(entity_id: str, mute: bool = True):
    alert_filter_create = AlertFilterCreate(
        entity_id=entity_id,
        id_type=get_id_type(entity_id),
        exclude=mute,
    )
    new_filter_or_message = create_alert_filter_db(alert_filter_create)
    if not new_filter_or_message or isinstance(new_filter_or_message, str):
        logger.info(
            f"Filter for {entity_id} already exists. Updating it."
        )
        alert_filter_update = AlertFilterUpdate(exclude=mute)
        update_alert_filter_by_entity_id(entity_id, alert_filter_update)
    else:
        logger.info(f"Created filter for {entity_id} successfully")
    logger.info(f"Successfully {'muted' if mute else 'unmuted'} {entity_id} successfully")
    return True
