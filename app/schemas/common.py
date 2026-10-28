from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str
