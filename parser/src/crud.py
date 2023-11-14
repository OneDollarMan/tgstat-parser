import models
from db_init import session


def get_category_by_name(name: str):
    return session.query(models.TelegramCategory).filter(models.TelegramCategory.name == name).first()


def save_category(category: models.TelegramCategory):
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def save_entity(entity: models.TelegramEntity):
    db_entity = session.query(models.TelegramEntity).filter(models.TelegramEntity.url == entity.url).first()
    if db_entity is None:
        session.add(entity)
        session.commit()
        return True
    else:
        return False


def get_entity_by_url(url: str):
    return session.query(models.TelegramEntity).filter(models.TelegramEntity.url == url).first()
