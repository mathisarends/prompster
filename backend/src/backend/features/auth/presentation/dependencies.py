# import logging
# from typing import Annotated
# from uuid import UUID

# from fastapi import (
#     Depends,
#     HTTPException,
#     Request,
#     WebSocket,
#     WebSocketException,
#     status,
# )

# from backend.features.auth.application.schemas import TokenPayload
# from backend.features.auth.infrastructure import AuthConfig
# from backend.features.auth.infrastructure.jwt import JwtTokenIssuer
# from backend.features.user.domain.views import UserRole

# logger = logging.getLogger(__name__)


# def _get_jwt_config() -> AuthConfig:
#     return AuthConfig()


# def _get_token_service(
#     jwt_config: Annotated[AuthConfig, Depends(_get_jwt_config)],
# ) -> JwtTokenIssuer:
#     return JwtTokenIssuer(config=jwt_config)


# async def _get_authenticated_token_payload(
#     request: Request,
#     jwt_config: Annotated[AuthConfig, Depends(_get_jwt_config)],
#     token_service: Annotated[JwtTokenIssuer, Depends(_get_token_service)],
# ) -> TokenPayload:
#     token = request.cookies.get(jwt_config.access_token_cookie_name)
#     if not token:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
#         )

#     return token_service.validate(token)


# async def _get_authenticated_token_payload_for_websocket(
#     websocket: WebSocket,
#     jwt_config: Annotated[AuthConfig, Depends(_get_jwt_config)],
#     token_service: Annotated[JwtTokenIssuer, Depends(_get_token_service)],
# ) -> TokenPayload:
#     token = websocket.cookies.get(jwt_config.access_token_cookie_name)
#     logger.debug(
#         "WebSocket auth: cookie_name=%s token_present=%s",
#         jwt_config.access_token_cookie_name,
#         bool(token),
#     )
#     if not token:
#         logger.warning(
#             "WebSocket rejected – no access token cookie (cookie_name=%s, path=%s)",
#             jwt_config.access_token_cookie_name,
#             websocket.url.path,
#         )
#         raise WebSocketException(
#             code=status.WS_1008_POLICY_VIOLATION, reason="Access token required"
#         )

#     try:
#         return token_service.validate(token)
#     except Exception as exc:
#         logger.warning(
#             "WebSocket rejected – token validation failed (path=%s): %s",
#             websocket.url.path,
#             exc,
#         )
#         raise WebSocketException(
#             code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token"
#         ) from exc


# async def _get_authenticated_user_id(
#     payload: Annotated[TokenPayload, Depends(_get_authenticated_token_payload)],
# ) -> UUID:
#     return payload.user_id


# async def _get_authenticated_user_role(
#     payload: Annotated[TokenPayload, Depends(_get_authenticated_token_payload)],
# ) -> UserRole:
#     return payload.role


# async def _get_authenticated_user_id_for_websocket(
#     payload: Annotated[
#         TokenPayload, Depends(_get_authenticated_token_payload_for_websocket)
#     ],
# ) -> UUID:
#     return payload.user_id


# async def _get_authenticated_user_role_for_websocket(
#     payload: Annotated[
#         TokenPayload, Depends(_get_authenticated_token_payload_for_websocket)
#     ],
# ) -> UserRole:
#     return payload.role


# AuthenticatedUserId = Annotated[UUID, Depends(_get_authenticated_user_id)]
# AuthenticatedUserRole = Annotated[UserRole, Depends(_get_authenticated_user_role)]
# AuthenticatedUserIdForWebsocket = Annotated[
#     UUID, Depends(_get_authenticated_user_id_for_websocket)
# ]
# AuthenticatedUserRoleForWebsocket = Annotated[
#     UserRole, Depends(_get_authenticated_user_role_for_websocket)
# ]
