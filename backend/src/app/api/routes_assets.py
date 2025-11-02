"""媒体素材管理 API - 背景音乐、图片等素材"""
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MediaAsset
from app.services.storage_service import StorageSaveResult, StorageService

router = APIRouter(prefix="/api/v1/assets", tags=["素材管理"])

_storage_service = StorageService()


# ==================== Schemas ====================


class MediaAssetBase(BaseModel):
    asset_type: Optional[str] = Field(None, description="素材类型: bgm, image, video, template")
    asset_name: Optional[str] = Field(None, description="素材名称")
    file_url: Optional[str] = Field(None, description="文件URL")
    file_path: Optional[str] = Field(None, description="本地路径")
    duration: Optional[float] = Field(None, description="时长（秒）")
    file_size: Optional[int] = Field(None, description="文件大小（字节）")
    tags: Optional[List[str]] = Field(None, description="标签")
    description: Optional[str] = Field(None, description="描述")
    is_default: Optional[bool] = Field(None, description="是否默认")
    is_active: Optional[bool] = Field(None, description="是否启用")
    meta_info: Optional[dict] = Field(None, description="元数据")


class MediaAssetCreate(MediaAssetBase):
    asset_type: str = Field(..., description="素材类型: bgm, image, video, template")
    asset_name: str = Field(..., description="素材名称")
    file_url: str = Field(..., description="文件URL")


class MediaAssetUpdate(MediaAssetBase):
    pass


class MediaAssetResponse(BaseModel):
    id: int
    asset_type: str
    asset_name: str
    file_url: str
    file_full_url: Optional[str]
    file_path: Optional[str]
    duration: Optional[float]
    file_size: Optional[int]
    tags: Optional[List[str]]
    description: Optional[str]
    is_default: bool
    is_active: bool
    meta_info: Optional[dict]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class MediaAssetUploadResponse(BaseModel):
    asset_type: str
    relative_path: str
    api_path: str
    full_url: Optional[str]
    file_path: str
    file_size: int
    content_type: Optional[str]


def _ensure_unique(db: Session, asset_type: str, asset_name: str, ignore_id: Optional[int] = None) -> None:
    query = db.query(MediaAsset.id).filter(
        MediaAsset.asset_type == asset_type,
        func.lower(MediaAsset.asset_name) == func.lower(asset_name),
    )
    if ignore_id is not None:
        query = query.filter(MediaAsset.id != ignore_id)
    exists = db.query(query.exists()).scalar()
    if exists:
        raise HTTPException(status_code=409, detail="同类型素材名称已存在")


def _serialize_asset(asset: MediaAsset) -> Dict[str, Any]:
    data = asset.to_dict()
    data["file_full_url"] = _storage_service.build_full_url(data.get("file_url"))
    return data


def _normalise_file_url(raw_path: str) -> str:
    value = (raw_path or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="文件URL不能为空")

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"}:
        return value

    try:
        return _storage_service.ensure_api_path(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _derive_file_path(api_path: str) -> Optional[str]:
    try:
        return str(_storage_service.to_absolute_path(api_path))
    except Exception:
        return None


# ==================== API ====================


@router.post("/", response_model=MediaAssetResponse, summary="添加素材")
def create_asset(asset: MediaAssetCreate, db: Session = Depends(get_db)):
    """添加新的媒体素材（背景音乐、图片等）"""
    _ensure_unique(db, asset.asset_type, asset.asset_name)

    normalised_url = _normalise_file_url(asset.file_url)

    file_path_value: Optional[str]
    if isinstance(asset.file_path, str) and asset.file_path.strip():
        file_path_value = asset.file_path.strip()
    else:
        file_path_value = _derive_file_path(normalised_url)

    file_size_value = asset.file_size
    if file_size_value is None and file_path_value:
        try:
            file_size_value = Path(file_path_value).stat().st_size
        except OSError:
            pass

    db_asset = MediaAsset(
        asset_type=asset.asset_type.strip(),
        asset_name=asset.asset_name.strip(),
        file_url=normalised_url,
        file_path=file_path_value,
        duration=asset.duration,
        file_size=file_size_value,
        tags=asset.tags,
        description=asset.description,
        is_default=bool(asset.is_default) if asset.is_default is not None else False,
        is_active=bool(asset.is_active) if asset.is_active is not None else True,
        meta_info=asset.meta_info,
    )
    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)

    return _serialize_asset(db_asset)


@router.post("/upload", response_model=MediaAssetUploadResponse, summary="上传素材文件")
async def upload_asset_file(
    asset_type: str = Form(..., description="素材类型"),
    file: UploadFile = File(..., description="素材文件"),
):
    """上传素材文件到本地存储并返回访问路径。"""

    if not asset_type or not asset_type.strip():
        raise HTTPException(status_code=400, detail="素材类型不能为空")

    result: StorageSaveResult = await run_in_threadpool(_storage_service.save_upload, asset_type, file)

    return MediaAssetUploadResponse(
        asset_type=asset_type.strip(),
        relative_path=result.relative_path,
        api_path=result.api_path,
        full_url=_storage_service.build_full_url(result.api_path),
        file_path=str(result.absolute_path),
        file_size=result.file_size,
        content_type=result.content_type,
    )


@router.get("/", response_model=List[MediaAssetResponse], summary="获取素材列表")
def list_assets(
    asset_type: Optional[str] = Query(None, description="筛选类型: bgm, image, video"),
    tags: Optional[str] = Query(None, description="筛选标签（逗号分隔）"),
    keyword: Optional[str] = Query(None, description="按名称模糊搜索"),
    is_active: Optional[bool] = Query(True, description="是否只显示启用的，为 None 时返回全部"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
):
    """获取素材列表，可筛选类型、标签、名称并分页"""
    query = db.query(MediaAsset)

    if asset_type:
        query = query.filter(MediaAsset.asset_type == asset_type)

    if is_active is True:
        query = query.filter(MediaAsset.is_active.is_(True))
    elif is_active is False:
        query = query.filter(MediaAsset.is_active.is_(False))

    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(MediaAsset.asset_name.ilike(pattern))

    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tag_list:
            query = query.filter(MediaAsset.tags.contains(tag))

    assets = (
        query.order_by(MediaAsset.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [_serialize_asset(asset) for asset in assets]


@router.get("/bgm", response_model=List[MediaAssetResponse], summary="获取背景音乐列表")
def list_bgm(db: Session = Depends(get_db)):
    """快捷接口：获取所有背景音乐"""
    assets = (
        db.query(MediaAsset)
        .filter(MediaAsset.asset_type == "bgm", MediaAsset.is_active.is_(True))
        .order_by(MediaAsset.asset_name.asc())
        .all()
    )
    return [_serialize_asset(asset) for asset in assets]


@router.get("/{asset_id}", response_model=MediaAssetResponse, summary="获取素材详情")
def get_asset(asset_id: int, db: Session = Depends(get_db)):
    """获取单个素材的详细信息"""
    asset = db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")
    return _serialize_asset(asset)


@router.put("/{asset_id}", response_model=MediaAssetResponse, summary="更新素材")
def update_asset(asset_id: int, asset_update: MediaAssetUpdate, db: Session = Depends(get_db)):
    """更新素材信息（整体或部分）"""
    asset = db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    payload = asset_update.model_dump(exclude_unset=True)
    if not payload:
        return _serialize_asset(asset)

    new_type = payload.get("asset_type", asset.asset_type)
    new_name = payload.get("asset_name", asset.asset_name)
    if new_type and new_name:
        _ensure_unique(db, new_type, new_name, ignore_id=asset_id)

    for key, value in payload.items():
        if key == "file_url" and isinstance(value, str):
            normalised = _normalise_file_url(value)
            setattr(asset, key, normalised)
            # Update file_path if not explicitly provided in payload
            if "file_path" not in payload:
                derived_path = _derive_file_path(normalised)
                if derived_path:
                    asset.file_path = derived_path
            continue
        setattr(asset, key, value)

    db.commit()
    db.refresh(asset)
    return _serialize_asset(asset)


@router.delete("/{asset_id}", summary="删除素材")
def delete_asset(
    asset_id: int,
    soft_delete: bool = Query(True, description="软删除（置为不启用）"),
    db: Session = Depends(get_db),
):
    """删除素材（默认软删除）"""
    asset = db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    if soft_delete:
        asset.is_active = False
        db.commit()
        return {"message": "素材已禁用"}

    db.delete(asset)
    db.commit()
    return {"message": "素材已删除"}


@router.post("/{asset_id}/set-default", summary="设为默认素材")
def set_default_asset(asset_id: int, db: Session = Depends(get_db)):
    """将某个素材设为默认（同类型其他素材取消默认）"""
    asset = db.get(MediaAsset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="素材不存在")

    db.query(MediaAsset).filter(
        MediaAsset.asset_type == asset.asset_type,
        MediaAsset.id != asset_id,
    ).update({"is_default": False})

    asset.is_default = True
    asset.is_active = True
    db.commit()

    return {"message": f"{asset.asset_name} 已设为默认{asset.asset_type}"}
