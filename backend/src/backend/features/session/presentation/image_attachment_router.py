from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, File, UploadFile, status

from backend.features.auth.presentation.dependencies import AuthenticatedUserId
from backend.features.session.application import (
    ImageAttachmentService,
    SessionImageAttachmentUpload,
)
from backend.features.session.application.ports import MessageAttachmentStore
from backend.features.session.presentation.schemas import (
    ErrorResponse,
    UploadedImageAttachmentResponse,
)

image_attachment_router = APIRouter(
    route_class=DishkaRoute,
    prefix="/image-attachments",
    tags=["image-attachments"],
)

_auth_errors = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
}
_bad_request = {status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse}}


@image_attachment_router.post(
    "",
    response_model=UploadedImageAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="upload_image_attachment",
    responses=_auth_errors | _bad_request,
)
async def upload_image_attachment(
    authenticated_user_id: AuthenticatedUserId,
    service: FromDishka[ImageAttachmentService],
    attachment_store: FromDishka[MessageAttachmentStore],
    file: Annotated[UploadFile, File()],
) -> UploadedImageAttachmentResponse:
    image = await service.stash_image(
        user_id=authenticated_user_id,
        image=SessionImageAttachmentUpload(
            file_name=file.filename or "attachment",
            content_type=file.content_type or "application/octet-stream",
            content=await file.read(),
        ),
    )
    url = await attachment_store.create_signed_url(
        storage_key=image.storage_key,
        expires_in_seconds=900,
    )
    return UploadedImageAttachmentResponse(
        id=image.id,
        storage_key=image.storage_key,
        url=url,
        content_type=image.content_type,
        file_name=image.file_name,
        size_bytes=image.size_bytes,
    )
