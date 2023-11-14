import os
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

db_url = f'postgresql://{os.environ.get("POSTGRES_USER")}:{os.environ.get("POSTGRES_PASSWORD")}@{os.environ.get("POSTGRES_HOST")}:{os.environ.get("POSTGRES_PORT")}/{os.environ.get("POSTGRES_DB")}'
engine = create_engine(db_url, echo=False)
Session = sessionmaker(bind=engine, expire_on_commit=False)
session = Session()
Base = declarative_base(metadata=sqlalchemy.MetaData())
