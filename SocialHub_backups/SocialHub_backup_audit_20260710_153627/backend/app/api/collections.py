"""Saved Collections - Feature 4"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from ..database import get_db
from ..models.models import User, SavedCollection, CollectionItem, Post, Reel
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/api/collections", tags=["Collections"])


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class UpdateCollectionRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)


@router.get("")
def get_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all collections for current user."""
    collections = db.query(SavedCollection).filter(
        SavedCollection.user_id == current_user.id
    ).order_by(SavedCollection.updated_at.desc()).all()
    
    result = []
    for col in collections:
        items = db.query(CollectionItem).filter(CollectionItem.collection_id == col.id).count()
        result.append({
            "id": col.id,
            "name": col.name,
            "cover_url": col.cover_url,
            "items_count": items,
            "created_at": str(col.created_at),
            "updated_at": str(col.updated_at),
        })
    return {"collections": result}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_collection(
    request: CreateCollectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new collection."""
    existing = db.query(SavedCollection).filter(
        SavedCollection.user_id == current_user.id,
        SavedCollection.name == request.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Collection with this name already exists")
    
    col = SavedCollection(user_id=current_user.id, name=request.name)
    db.add(col)
    db.commit()
    db.refresh(col)
    return {"id": col.id, "name": col.name, "message": "Collection created"}


@router.put("/{collection_id}")
def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Rename collection."""
    col = db.query(SavedCollection).filter(
        SavedCollection.id == collection_id,
        SavedCollection.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    if request.name:
        existing = db.query(SavedCollection).filter(
            SavedCollection.user_id == current_user.id,
            SavedCollection.name == request.name,
            SavedCollection.id != collection_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Collection with this name already exists")
        col.name = request.name
    
    db.commit()
    return {"message": "Collection updated", "name": col.name}


@router.delete("/{collection_id}")
def delete_collection(
    collection_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a collection."""
    col = db.query(SavedCollection).filter(
        SavedCollection.id == collection_id,
        SavedCollection.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    db.delete(col)
    db.commit()
    return {"message": "Collection deleted"}


@router.delete("/saved/{saved_id}")
def delete_saved_item_alias(
    saved_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete one saved collection item by id for /api/saved/{saved_id} alias routers."""
    item = db.query(CollectionItem).join(SavedCollection).filter(
        CollectionItem.id == saved_id,
        SavedCollection.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Saved item not found")
    db.delete(item)
    db.commit()
    return {"message": "Saved item removed"}


@router.get("/{collection_id}/items")
def get_collection_items(
    collection_id: str,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get items in a collection."""
    col = db.query(SavedCollection).filter(
        SavedCollection.id == collection_id,
        SavedCollection.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    offset = (page - 1) * page_size
    items = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id
    ).offset(offset).limit(page_size).all()
    
    posts = []
    reels_list = []
    for item in items:
        if item.post_id:
            post = db.query(Post).filter(Post.id == item.post_id).first()
            if post and not post.is_deleted:
                posts.append({
                    "id": post.id, "content": post.content,
                    "image": post.images[0].image_url if post.images else None,
                    "created_at": str(post.created_at),
                    "author": {"id": post.author.id, "username": post.author.username, "profile_picture": post.author.profile_picture} if post.author else None,
                })
        if item.reel_id:
            reel = db.query(Reel).filter(Reel.id == item.reel_id).first()
            if reel and not reel.is_deleted:
                reels_list.append({
                    "id": reel.id, "caption": reel.caption,
                    "thumbnail_url": reel.thumbnail_url,
                    "video_url": reel.video_url,
                    "created_at": str(reel.created_at),
                })
    
    total = db.query(CollectionItem).filter(CollectionItem.collection_id == collection_id).count()
    return {
        "collection": {"id": col.id, "name": col.name},
        "posts": posts,
        "reels": reels_list,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/{collection_id}/add")
def add_to_collection(
    collection_id: str,
    post_id: Optional[str] = None,
    reel_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add post or reel to collection."""
    col = db.query(SavedCollection).filter(
        SavedCollection.id == collection_id,
        SavedCollection.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    if not post_id and not reel_id:
        raise HTTPException(status_code=400, detail="Provide post_id or reel_id")
    
    if post_id:
        existing = db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id,
            CollectionItem.post_id == post_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Post already in collection")
        item = CollectionItem(collection_id=collection_id, post_id=post_id)
        db.add(item)
    
    if reel_id:
        existing = db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id,
            CollectionItem.reel_id == reel_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Reel already in collection")
        item = CollectionItem(collection_id=collection_id, reel_id=reel_id)
        db.add(item)
    
    col.updated_at = db.query(SavedCollection.updated_at).filter(SavedCollection.id == collection_id).scalar()
    db.commit()
    return {"message": "Item added to collection"}


@router.delete("/{collection_id}/remove")
def remove_from_collection(
    collection_id: str,
    post_id: Optional[str] = None,
    reel_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove post or reel from collection."""
    col = db.query(SavedCollection).filter(
        SavedCollection.id == collection_id,
        SavedCollection.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    if post_id:
        item = db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id,
            CollectionItem.post_id == post_id
        ).first()
        if item:
            db.delete(item)
    
    if reel_id:
        item = db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id,
            CollectionItem.reel_id == reel_id
        ).first()
        if item:
            db.delete(item)
    
    db.commit()
    return {"message": "Item removed from collection"}