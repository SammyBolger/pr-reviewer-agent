from app.review.cost import estimate_cost_usd


def test_haiku_cost():
    # 1000 in + 500 out for haiku
    cost = estimate_cost_usd("claude-haiku-4-5", 1000, 500)
    # 1000 * 1.0 / 1M + 500 * 5.0 / 1M = 0.001 + 0.0025 = 0.0035
    assert abs(cost - 0.0035) < 1e-6


def test_sonnet_cost():
    cost = estimate_cost_usd("claude-sonnet-4-6", 1000, 500)
    # 1000 * 3.0 / 1M + 500 * 15.0 / 1M = 0.003 + 0.0075 = 0.0105
    assert abs(cost - 0.0105) < 1e-6


def test_unknown_model_returns_zero():
    assert estimate_cost_usd("some-other-model", 1000, 1000) == 0.0


def test_full_dated_model_name_is_matched():
    # dated variants like claude-haiku-4-5-20251001 should still price correctly
    cost = estimate_cost_usd("claude-haiku-4-5-20251001", 1000, 500)
    assert abs(cost - 0.0035) < 1e-6
