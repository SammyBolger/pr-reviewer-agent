# Approximate Anthropic pricing per 1M tokens as of 2026-08.
# Update as prices change.

PRICING: dict[str, tuple[float, float]] = {
    # model prefix -> (input $/M, output $/M)
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-opus-4-7": (15.0, 75.0),
}


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    for prefix, (in_price, out_price) in PRICING.items():
        if model.startswith(prefix):
            return round(
                (tokens_in * in_price + tokens_out * out_price) / 1_000_000,
                6,
            )
    return 0.0
