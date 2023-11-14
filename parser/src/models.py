import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from db_init import Base


class TypeEnum(enum.Enum):
    channel = 1
    chat = 2


class TelegramCategory(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    entities = relationship("TelegramEntity", back_populates="category")


class TelegramEntity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    type = Column(Enum(TypeEnum))
    subs_count = Column(Integer)
    description = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"))

    category = relationship("TelegramCategory", back_populates="entities")
