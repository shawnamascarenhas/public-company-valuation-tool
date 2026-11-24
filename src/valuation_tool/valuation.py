"""Enterprise-value and equity-value bridge calculations."""


def enterprise_to_equity_value(
    enterprise_value: float,
    *,
    total_debt: float,
    cash: float,
    non_controlling_interest: float = 0.0,
    preferred_stock: float = 0.0,
    investments: float = 0.0,
) -> float:
    """Convert enterprise value to common equity value.

    All inputs use the same monetary unit. The MVP treats non-operating
    investments as an equity-value addition, consistent with cash.
    """
    return (
        enterprise_value
        - total_debt
        - non_controlling_interest
        - preferred_stock
        + cash
        + investments
    )


def equity_to_enterprise_value(
    equity_value: float,
    *,
    total_debt: float,
    cash: float,
    non_controlling_interest: float = 0.0,
    preferred_stock: float = 0.0,
    investments: float = 0.0,
) -> float:
    """Convert common equity value to enterprise value."""
    return (
        equity_value
        + total_debt
        + non_controlling_interest
        + preferred_stock
        - cash
        - investments
    )


def per_share_value(equity_value: float, diluted_shares: float) -> float:
    """Calculate value per diluted share, rejecting invalid share counts."""
    if diluted_shares <= 0:
        raise ValueError("Diluted shares must be greater than zero")
    return equity_value / diluted_shares
