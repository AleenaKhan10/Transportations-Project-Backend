from sqlmodel import Session, select
from passlib.context import CryptContext
from db.models import User
from db.database import engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_user(user_data: User):
    with Session(engine) as session:
        user = User(username=user_data.username, password=pwd_context.hash(user_data.password))
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

def authenticate_user(user_data: User):
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == user_data.username)).first()
        if not user or not pwd_context.verify(user_data.password, user.password):
            return None
        return user

