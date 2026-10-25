"""Expose anticipated failures to MCP callers without treating them as crashes."""

import inspect
from functools import wraps
from xml.etree.ElementTree import ParseError

from defusedxml.common import DefusedXmlException
from mcp.server.mcpserver.exceptions import ToolError
from PIL.Image import DecompressionBombError, DecompressionBombWarning

EXPECTED = (ValueError, OSError, ParseError, DefusedXmlException,
            DecompressionBombError, DecompressionBombWarning)


def tool_errors(function):
    if inspect.iscoroutinefunction(function):
        @wraps(function)
        async def asynchronous(*args, **kwargs):
            try:
                return await function(*args, **kwargs)
            except EXPECTED as error:
                raise ToolError(str(error)) from error
        return asynchronous

    @wraps(function)
    def synchronous(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except EXPECTED as error:
            raise ToolError(str(error)) from error
    return synchronous
