"""Tests for probe.validate_payloads."""
import pytest

from probe import validate_payloads


def test_list_of_strings_returns_same_list():
    payloads = ["a", "b", "c"]
    assert validate_payloads(payloads) == payloads


def test_empty_list_is_valid():
    assert validate_payloads([]) == []


def test_not_a_list_raises():
    with pytest.raises(ValueError, match="JSON array of strings"):
        validate_payloads({"a": 1})


def test_list_with_non_string_raises():
    with pytest.raises(ValueError, match="JSON array of strings"):
        validate_payloads(["ok", 42, "also ok"])


def test_none_raises():
    with pytest.raises(ValueError):
        validate_payloads(None)
