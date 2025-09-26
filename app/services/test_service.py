from fastapi import APIRouter
from models import test_modal
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(
    prefix="/test_books",
    tags=["test_books"]
)




@router.get("/", response_model=list[test_modal.TestBook])
def get_books():
    return test_modal.get_all_books()

@router.get("/book/{book_id}", response_model=test_modal.TestBook)
def get_book_id(book_id:int):
    book = test_modal.get_id_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="book not found") 
    return book