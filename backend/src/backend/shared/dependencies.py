from fastapi import Depends
from fastapi.params import Depends as DependsParam
from starlette.requests import HTTPConnection


def dishka_ws_dep[T](cls: type[T]) -> DependsParam:
    async def _get(conn: HTTPConnection) -> T:
        return await conn.state.dishka_container.get(cls)

    return Depends(_get)
