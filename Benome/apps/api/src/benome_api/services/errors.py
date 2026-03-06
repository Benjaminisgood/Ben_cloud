from __future__ import annotations
from enum import Enum


class ServiceErrorCode(str, Enum):
    """服务错误代码"""
    INVALID_INPUT = "INVALID_INPUT"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ServiceError(Exception):
    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        code: ServiceErrorCode = ServiceErrorCode.INVALID_INPUT,
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.code = code
