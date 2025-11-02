"""配置管理 API - 凭证和可选参数管理"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import ServiceCredential, ServiceOption

router = APIRouter(prefix="/api/v1/config", tags=["配置管理"])


# ==================== Schemas ====================

class ServiceCredentialCreate(BaseModel):
    service_name: str = Field(..., description="服务名称")
    credential_type: str = Field(default="api_key", description="凭证类型")
    credential_key: Optional[str] = Field(None, description="API Key")
    credential_secret: Optional[str] = Field(None, description="Secret Key")
    api_url: Optional[str] = Field(None, description="API URL")
    description: Optional[str] = Field(None, description="描述")
    is_active: bool = Field(default=True, description="是否启用")


class ServiceCredentialUpdate(BaseModel):
    service_name: Optional[str] = Field(None, description="服务名称")
    credential_type: Optional[str] = Field(None, description="凭证类型")
    credential_key: Optional[str] = Field(None, description="API Key")
    credential_secret: Optional[str] = Field(None, description="Secret Key")
    api_url: Optional[str] = Field(None, description="API URL")
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[bool] = Field(None, description="是否启用")


class ServiceCredentialResponse(BaseModel):
    id: int
    service_name: str
    credential_type: str
    credential_key: Optional[str]  # 脱敏后的
    api_url: Optional[str]
    is_active: bool
    description: Optional[str]
    last_used_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class ServiceOptionCreate(BaseModel):
    service_name: str = Field(..., description="服务名称")
    option_type: str = Field(..., description="选项类型")
    option_key: str = Field(..., description="选项键")
    option_value: str = Field(..., description="选项值")
    option_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    is_default: bool = Field(default=False, description="是否默认")
    meta_data: Optional[dict] = Field(None, description="元数据")
    is_active: bool = Field(default=True, description="是否可用")


class ServiceOptionUpdate(BaseModel):
    service_name: Optional[str] = Field(None, description="服务名称")
    option_type: Optional[str] = Field(None, description="选项类型")
    option_key: Optional[str] = Field(None, description="选项键")
    option_value: Optional[str] = Field(None, description="选项值")
    option_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="描述")
    is_default: Optional[bool] = Field(None, description="是否默认")
    meta_data: Optional[dict] = Field(None, description="元数据")
    is_active: Optional[bool] = Field(None, description="是否可用")


class ServiceOptionResponse(BaseModel):
    id: int
    service_name: str
    option_type: str
    option_key: str
    option_value: str
    option_name: Optional[str]
    description: Optional[str]
    is_default: bool
    is_active: bool
    meta_data: Optional[dict]
    
    class Config:
        from_attributes = True


# ==================== 凭证管理 API ====================

@router.post("/credentials", response_model=ServiceCredentialResponse, summary="添加服务凭证")
def create_credential(
    credential: ServiceCredentialCreate,
    db: Session = Depends(get_db)
):
    """添加新的服务凭证（API Key 等）"""
    db_credential = ServiceCredential(
        service_name=credential.service_name,
        credential_type=credential.credential_type,
        credential_key=credential.credential_key,
        credential_secret=credential.credential_secret,
        api_url=credential.api_url,
        description=credential.description,
        is_active=credential.is_active,
    )
    db.add(db_credential)
    db.commit()
    db.refresh(db_credential)
    
    return db_credential.to_dict(include_secret=False)


@router.get("/credentials", response_model=List[ServiceCredentialResponse], summary="获取所有凭证")
def list_credentials(
    service_name: Optional[str] = Query(None, description="筛选服务名称"),
    is_active: Optional[bool] = Query(None, description="筛选是否启用"),
    db: Session = Depends(get_db)
):
    """获取凭证列表（敏感信息脱敏）"""
    query = db.query(ServiceCredential)
    
    if service_name:
        query = query.filter(ServiceCredential.service_name == service_name)
    if is_active is not None:
        query = query.filter(ServiceCredential.is_active == is_active)
    
    credentials = query.all()
    
    return [cred.to_dict(include_secret=False) for cred in credentials]


@router.get("/credentials/{credential_id}", response_model=ServiceCredentialResponse, summary="获取单个凭证详情")
def get_credential(
    credential_id: int,
    include_secret: bool = Query(False, description="是否包含敏感信息"),
    db: Session = Depends(get_db)
):
    """获取凭证详情"""
    credential = db.query(ServiceCredential).filter(ServiceCredential.id == credential_id).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    
    return credential.to_dict(include_secret=include_secret)


@router.patch("/credentials/{credential_id}", response_model=ServiceCredentialResponse, summary="更新凭证")
def update_credential(
    credential_id: int,
    payload: ServiceCredentialUpdate,
    db: Session = Depends(get_db)
):
    """更新服务凭证信息"""
    credential = db.query(ServiceCredential).filter(ServiceCredential.id == credential_id).first()
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")

    update_data = payload.dict(exclude_unset=True)

    target_service = update_data.get("service_name", credential.service_name)
    target_type = update_data.get("credential_type", credential.credential_type)
    target_key = update_data.get("credential_key", credential.credential_key)

    # 只有当 service_name/credential_type/credential_key 发生变更时才做唯一性检查
    key_fields = ["service_name", "credential_type", "credential_key"]
    key_changed = any(f in update_data for f in key_fields)
    if key_changed:
        exists = (
            db.query(ServiceCredential)
            .filter(
                ServiceCredential.service_name == target_service,
                ServiceCredential.credential_type == target_type,
                ServiceCredential.credential_key == target_key,
                ServiceCredential.id != credential.id,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="该服务的凭证已存在，无法重复添加")
    for field, value in update_data.items():
        setattr(credential, field, value)

    db.commit()
    db.refresh(credential)

    return credential.to_dict(include_secret=False)


@router.delete("/credentials/{credential_id}", summary="删除凭证")
def delete_credential(
    credential_id: int,
    db: Session = Depends(get_db)
):
    """删除服务凭证"""
    credential = db.query(ServiceCredential).filter(ServiceCredential.id == credential_id).first()
    
    if not credential:
        raise HTTPException(status_code=404, detail="凭证不存在")
    
    db.delete(credential)
    db.commit()
    
    return {"message": "删除成功"}


# ==================== 可选参数管理 API ====================

@router.post("/options", response_model=ServiceOptionResponse, summary="添加可选参数")
def create_option(
    option: ServiceOptionCreate,
    db: Session = Depends(get_db)
):
    """添加新的可选参数（如音色ID、LoRA ID等）"""
    db_option = ServiceOption(
        service_name=option.service_name,
        option_type=option.option_type,
        option_key=option.option_key,
        option_value=option.option_value,
        option_name=option.option_name,
        description=option.description,
        is_default=option.is_default,
        is_active=option.is_active,
        meta_data=option.meta_data,
    )
    db.add(db_option)
    db.commit()
    db.refresh(db_option)
    
    return db_option.to_dict()


@router.get("/options", response_model=List[ServiceOptionResponse], summary="获取可选参数列表")
def list_options(
    service_name: Optional[str] = Query(None, description="服务名称"),
    option_type: Optional[str] = Query(None, description="选项类型"),
    is_active: Optional[bool] = Query(None, description="筛选可用状态"),
    db: Session = Depends(get_db)
):
    """
    获取可选参数列表
    
    Examples:
    - GET /api/v1/config/options?service_name=fishaudio&option_type=voice_id  # 获取所有音色
    - GET /api/v1/config/options?service_name=liblib&option_type=lora_id     # 获取所有 LoRA
    """
    query = db.query(ServiceOption)
    
    if service_name:
        query = query.filter(ServiceOption.service_name == service_name)
    if option_type:
        query = query.filter(ServiceOption.option_type == option_type)
    if is_active is not None:
        query = query.filter(ServiceOption.is_active == is_active)
    
    options = query.all()
    
    return [opt.to_dict() for opt in options]


@router.get("/options/voices", response_model=List[ServiceOptionResponse], summary="获取所有音色")
def list_voices(db: Session = Depends(get_db)):
    """快捷接口：获取所有可用的音色列表"""
    voices = db.query(ServiceOption).filter(
        ServiceOption.service_name == "fishaudio",
        ServiceOption.option_type == "voice_id"
    ).all()
    return [v.to_dict() for v in voices]


@router.get("/options/loras", response_model=List[ServiceOptionResponse], summary="获取所有 LoRA")
def list_loras(db: Session = Depends(get_db)):
    """快捷接口：获取所有可用的 LoRA 模型"""
    loras = db.query(ServiceOption).filter(
        ServiceOption.service_name == "liblib",
        ServiceOption.option_type == "lora_id"
    ).all()
    return [l.to_dict() for l in loras]


@router.patch("/options/{option_id}", response_model=ServiceOptionResponse, summary="更新可选参数")
def update_option(
    option_id: int,
    payload: ServiceOptionUpdate,
    db: Session = Depends(get_db)
):
    """更新可选参数信息，并支持切换默认/可用状态"""
    option = db.query(ServiceOption).filter(ServiceOption.id == option_id).first()
    if not option:
        raise HTTPException(status_code=404, detail="参数不存在")

    update_data = payload.dict(exclude_unset=True)

    # 如果需要设置默认，将同类型其它选项清除默认标记
    if update_data.get("is_default") is True:
        target_service = update_data.get("service_name") or option.service_name
        target_type = update_data.get("option_type") or option.option_type
        db.query(ServiceOption).filter(
            ServiceOption.service_name == target_service,
            ServiceOption.option_type == target_type,
            ServiceOption.id != option.id,
        ).update({ServiceOption.is_default: False}, synchronize_session=False)

    for field, value in update_data.items():
        setattr(option, field, value)

    db.commit()
    db.refresh(option)

    return option.to_dict()


@router.delete("/options/{option_id}", summary="删除可选参数")
def delete_option(
    option_id: int,
    db: Session = Depends(get_db)
):
    """删除可选参数"""
    option = db.query(ServiceOption).filter(ServiceOption.id == option_id).first()
    
    if not option:
        raise HTTPException(status_code=404, detail="参数不存在")
    
    db.delete(option)
    db.commit()
    
    return {"message": "删除成功"}
