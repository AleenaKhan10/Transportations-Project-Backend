from pydantic import BaseModel
from typing import List, Optional
import logging


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TestBook(BaseModel):
    id: int
    title: str
    author: str

    @classmethod
    def fake_books(cls) -> List["TestBook"]:
        logger.info("Generating fake books dataset...")
        return [
            cls(id=1, title="Clean Code", author="Robert C. Martin"),
            cls(id=2, title="The Pragmatic Programmer", author="Andrew Hunt"),
            cls(id=3, title="The Pragmatic Programmer", author="ibrar malik"),
        ]


def get_all_books() -> list[TestBook]:
    logger.info("Fetching all books (count=%d)", len(TestBook.fake_books()))
    return TestBook.fake_books()


def get_id_book(book_id: int) -> TestBook | None:
    logger.info("Fetching book with id=%d", book_id)
    for book in TestBook.fake_books():
        if book.id == book_id:
            return book

    return None
