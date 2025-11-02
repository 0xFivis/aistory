from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.story import Story
from pydantic import BaseModel

router = APIRouter(prefix="/stories", tags=["stories"])

class StoryCreate(BaseModel):
    title: str
    content: str

class StoryOut(BaseModel):
    id: int
    title: str
    content: str
    status: str

@router.post("/", response_model=StoryOut)
def create_story(payload: StoryCreate, db: Session = Depends(get_db)):
    story = Story(title=payload.title, content=payload.content)
    db.add(story)
    db.commit()
    db.refresh(story)
    return story

@router.get("/{story_id}", response_model=StoryOut)
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story
