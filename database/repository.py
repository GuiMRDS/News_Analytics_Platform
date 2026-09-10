from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
)

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(
        Integer,
        primary_key=True
    )

    topic = Column(
        String(255),
        nullable=False
    )

    title = Column(
        String(500)
    )

    content = Column(
        Text,
        nullable=False
    )

    workflow_version = Column(
        String(20),
        nullable=False
    )

    markdown_file = Column(
        String(255)
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )