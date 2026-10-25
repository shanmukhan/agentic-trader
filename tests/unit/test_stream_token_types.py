"""Configuration may be offline; selected broker identities cannot be coerced."""

import pytest
from pydantic import ValidationError

from trading_agent.settings import Settings


@pytest.mark.parametrize("token", [True, False, 1.0, "1", 0, -1])
def test_configured_stream_tokens_require_positive_integer_identity(token):
    with pytest.raises(ValidationError):
        Settings(stream_tokens=(token,))


def test_empty_selection_is_valid_for_offline_setup():
    assert Settings().stream_tokens == ()
    assert Settings(stream_tokens=(1, 257)).stream_tokens == (1, 257)
