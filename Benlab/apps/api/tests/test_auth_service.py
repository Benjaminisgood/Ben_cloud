from __future__ import annotations

from benlab_api.services.auth import validate_registration_input


def test_validate_registration_input_requires_required_fields() -> None:
    assert validate_registration_input("", "user1", "pass") == "请填写姓名、用户名和密码"
    assert validate_registration_input("Alice", "", "pass") == "请填写姓名、用户名和密码"
    assert validate_registration_input("Alice", "user1", "") == "请填写姓名、用户名和密码"


def test_validate_registration_input_accepts_complete_fields() -> None:
    assert validate_registration_input("Alice", "user1", "pass") is None
