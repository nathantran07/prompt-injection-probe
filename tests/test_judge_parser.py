"""Tests for probe.parse_judge_response."""
import json

import pytest

from probe import parse_judge_response


def test_plain_json():
    out = parse_judge_response('{"result": "BLOCKED", "reason": "refused politely"}')
    assert out == {"result": "BLOCKED", "reason": "refused politely"}


def test_json_with_markdown_fence():
    raw = '```json\n{"result": "INJECTED", "reason": "leaked the prompt"}\n```'
    out = parse_judge_response(raw)
    assert out == {"result": "INJECTED", "reason": "leaked the prompt"}


def test_json_with_bare_fence():
    raw = '```\n{"result": "BLOCKED", "reason": "ok"}\n```'
    out = parse_judge_response(raw)
    assert out["result"] == "BLOCKED"


def test_json_with_surrounding_whitespace():
    raw = '   \n  {"result": "BLOCKED", "reason": "ok"}  \n  '
    out = parse_judge_response(raw)
    assert out["result"] == "BLOCKED"


def test_invalid_result_value_raises():
    with pytest.raises(ValueError, match="invalid result"):
        parse_judge_response('{"result": "MAYBE", "reason": "unsure"}')


def test_missing_reason_raises():
    with pytest.raises(ValueError, match="reason"):
        parse_judge_response('{"result": "BLOCKED"}')


def test_malformed_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_judge_response("not json at all")
