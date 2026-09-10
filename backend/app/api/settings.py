from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services import credentials as credentials_service

router = APIRouter(tags=["settings"])


class CredentialPut(BaseModel):
    api_key: str = Field(min_length=1)


class CredentialOut(BaseModel):
    provider: str
    status: str
    masked_key: str | None


@router.put("/settings/credentials/{provider}", response_model=CredentialOut)
def put_credential(provider: str, body: CredentialPut):
    result = credentials_service.set_credential(provider, body.api_key)
    return CredentialOut(**result)


@router.get("/settings/credentials/{provider}", response_model=CredentialOut)
def get_credential(provider: str):
    result = credentials_service.get_credential_status(provider)
    return CredentialOut(**result)
