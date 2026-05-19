from typing import TypedDict


class FunctionSchema(TypedDict):
    name: str
    description: str
    parameters: dict


class ToolSchema(TypedDict):
    type: str
    function: FunctionSchema
