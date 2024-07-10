import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)

class Token(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    address = Column(String, nullable=False)
    last_check = Column(DateTime, default=datetime.utcnow)
    last_price = Column(Float)

# Use the DATABASE_URL provided by Railway
database_url = os.environ.get('DATABASE_URL', 'sqlite:///crypto_alert_bot.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(database_url)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

def add_user(telegram_id):
    session = get_session()
    user = User(telegram_id=telegram_id)
    session.add(user)
    session.commit()
    session.close()

def add_token(telegram_id, token_address):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if not user:
        add_user(telegram_id)
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
    token = Token(user_id=user.id, address=token_address)
    session.add(token)
    session.commit()
    session.close()

def get_user_tokens(telegram_id):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        tokens = session.query(Token).filter_by(user_id=user.id).all()
        session.close()
        return [(token.address, token.last_check) for token in tokens]
    session.close()
    return []

def update_token_check(telegram_id, token_address, last_price):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        token = session.query(Token).filter_by(user_id=user.id, address=token_address).first()
        if token:
            token.last_check = datetime.utcnow()
            token.last_price = last_price
            session.commit()
    session.close()

def remove_token(telegram_id, token_address):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        token = session.query(Token).filter_by(user_id=user.id, address=token_address).first()
        if token:
            session.delete(token)
            session.commit()
    session.close()

def get_user_token_count(telegram_id):
    session = get_session()
    user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if user:
        count = session.query(Token).filter_by(user_id=user.id).count()
        session.close()
        return count
    session.close()
    return 0
