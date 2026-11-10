"""Local token estimates; never persist input or send it to a tokenizer service."""
import json

from .usage_policy import BudgetExceeded


def input_token_bound(payload, model, overhead=4096):
    """Count serialized request tokens plus framing allowance, not UTF-8 bytes.

    Counting the entire JSON includes configuration and escaped message text, so
    it deliberately overcounts the visible input. Hosted retrieval is reserved
    separately at full model context by the spending meter.
    """
    serialized = json.dumps(payload, ensure_ascii=False, default=str)
    try:
        import tiktoken
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # A configured tariff alone does not establish a tokenizer mapping.
            return len(serialized.encode('utf-8')) + overhead
        return len(encoding.encode(serialized, disallowed_special=())) + overhead
    except Exception:
        # Missing vocabulary/cache must not remove the spending guard.
        raise BudgetExceeded('tokenizer_unavailable') from None
