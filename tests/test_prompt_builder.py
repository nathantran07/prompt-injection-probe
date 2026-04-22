"""Tests for probe.build_judge_prompt."""
import re

from probe import build_judge_prompt


def test_contains_all_three_inputs():
    prompt = build_judge_prompt(
        system_prompt="SYS",
        payload="PAY",
        response="RES",
    )
    assert "SYS" in prompt
    assert "PAY" in prompt
    assert "RES" in prompt


def test_uses_nonced_tags():
    prompt = build_judge_prompt("s", "p", "r")
    m = re.search(r"<system_prompt_([0-9a-f]+)>", prompt)
    assert m is not None, "nonced opening tag not found"
    nonce = m.group(1)
    assert len(nonce) == 8  # secrets.token_hex(4) → 8 hex chars
    # Same nonce reused for all three tags in one call:
    assert f"</system_prompt_{nonce}>" in prompt
    assert f"<injection_payload_{nonce}>" in prompt
    assert f"<model_response_{nonce}>" in prompt


def test_nonce_varies_across_calls():
    a = build_judge_prompt("s", "p", "r")
    b = build_judge_prompt("s", "p", "r")
    assert a != b, "nonce should change between calls"


def test_requests_json_only_output():
    prompt = build_judge_prompt("s", "p", "r")
    assert "Return ONLY valid JSON" in prompt
    assert '"BLOCKED"' in prompt
    assert '"INJECTED"' in prompt
