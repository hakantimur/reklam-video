from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.errors import error_response
from app.core.db import get_session
from app.schemas.asset import AssetListOut, AssetOut
from app.services import assets as assets_service
from app.services.errors import ServiceError

router = APIRouter(tags=["assets"])


@router.post("/projects/{project_id}/assets", response_model=AssetOut, status_code=201)
async def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    type: str = Form(...),
    origin: str = Form(default="user_upload"),
    session: Session = Depends(get_session),
):
    try:
        asset = await assets_service.save_uploaded_asset(
            session, project_id, file, asset_type=type, origin=origin
        )
    except ServiceError as exc:
        return error_response(exc)
    return AssetOut.model_validate(asset)


@router.get("/projects/{project_id}/assets", response_model=AssetListOut)
def list_assets(
    project_id: str,
    type: str | None = None,
    origin: str | None = None,
    text: str | None = None,
    session: Session = Depends(get_session),
):
    try:
        items = assets_service.list_assets(session, project_id, type=type, origin=origin, text=text)
    except ServiceError as exc:
        return error_response(exc)
    return AssetListOut(items=[AssetOut.model_validate(a) for a in items])


@router.get("/assets/{asset_id}/content")
def get_asset_content(asset_id: str, session: Session = Depends(get_session)):
    """Range-capable file download, resolved server-side from an opaque
    asset id only — the client never supplies a filesystem path (spec 20.1).
    """

    try:
        asset, path = assets_service.resolve_asset_path(session, asset_id)
    except ServiceError as exc:
        return error_response(exc)
    return FileResponse(path, filename=path.name)
