# IMC Prosperity 4 - Round 5

This folder contains my Round 5 work for IMC Prosperity 4: the final strategy implementation, the local data snapshot I used for replay, and a short write-up of the modeling ideas behind the bot.

## Files

- `ROUND5.py` - main trader submitted in Round 5 style.
- `ROUND_5/` - local replay datasets available in this workspace.

## What the strategy is trying to do

The bot is built around adaptive fair-value estimation, passive market making, and a few structured relative-value trades.

At a high level, it combines:

1. Product-level fair values from recent order book dynamics.
2. Cross-sectional signals inside product families.
3. Synthetic-value relationships for special structures such as `PEBBLES`.
4. Dedicated relative-value modules for `GIFT_BASKET` and the `SNACKPACK` pair.
5. Inventory and drawdown controls so the strategy stays deployable rather than purely replay-optimized.

## Core modeling ideas

### 1. Mid-price, trend, and volatility tracking

For each product, the bot starts from the top-of-book midpoint

$$
m_t = \frac{b_t + a_t}{2}
$$

and maintains fast and slow exponential moving averages:

$$
\text{fast}_t = 0.85 \cdot \text{fast}_{t-1} + 0.15 \cdot m_t
$$

$$
\text{slow}_t = 0.98 \cdot \text{slow}_{t-1} + 0.02 \cdot m_t
$$

This gives a short-horizon trend signal

$$
\Delta_t = \text{fast}_t - \text{slow}_t
$$

which nudges fair value in the trend direction.

The bot also tracks a rolling volatility proxy from midpoint returns:

$$
\sigma_t^2 = 0.94 \cdot \sigma_{t-1}^2 + 0.06 \cdot (m_t - m_{t-1})^2
$$

That volatility estimate is used to decide whether a spread is worth quoting and how aggressively to size orders.

### 2. Fair value with order book imbalance

For many products the fair value is a midpoint plus a few small corrections:

$$
f_t \approx m_t + \text{trend adjustment} + \text{cross-sectional adjustment} + \text{flow adjustment}
$$

One of those corrections uses order book imbalance:

$$
\text{imbalance}_t = \frac{V^{bid}_t - V^{ask}_t}{V^{bid}_t + V^{ask}_t}
$$

If the book is heavy on one side, the bot shifts its fair value slightly in the opposite direction to avoid paying up into short-term pressure.

### 3. Group-relative residuals

Many Round 5 products naturally sit inside families such as `GALAXY`, `SLEEP`, `MICROCHIP`, `ROBOT`, `UV`, and `TRANSLATOR`.

For a product family `G`, the bot estimates a family center from the median of member mid-prices:

$$
c_t^{(G)} = \text{median}\{m_t^{(i)} : i \in G\}
$$

For each product `i` in that family it tracks a residual

$$
r_t^{(i)} = m_t^{(i)} - c_t^{(G)}
$$

and stores a short residual history in `traderData`. If a product becomes temporarily rich or cheap relative to its family, the bot leans back toward the family-adjusted fair value rather than treating the move as fully independent.

### 4. PEBBLES synthetic fair values

The `PEBBLES` family is treated with a stronger structural assumption: the five contracts should approximately add up to a stable total. If

$$
S_t = \sum_{i=1}^{5} P_t^{(i)}
$$

then the bot learns a slowly updated target constant `C_t` and infers a synthetic fair value for each contract by backing out the other four:

$$
\hat{P}_t^{(i)} = C_t - \sum_{j \neq i} P_t^{(j)}
$$

This is a clean way to turn a basket identity into single-name trading signals.

### 5. Basket arbitrage in IGNITH products

The `GIFT_BASKET` module compares the traded basket price against its component value:

$$
R_t = P_t^{basket} - \left(4P_t^{chocolate} + 6P_t^{strawberries} + P_t^{roses}\right)
$$

The strategy tracks an EMA and variance of this residual and only trades when the observed edge is large relative to residual volatility. In other words, it does not just trade a raw spread; it trades a normalized mispricing with a stability filter.

### 6. Snack pair spread

For the pair `SNACKPACK_CHOCOLATE` vs `SNACKPACK_VANILLA`, the bot monitors

$$
D_t = P_t^{chocolate} - P_t^{vanilla}
$$

and trades the pair only when the deviation from its learned mean is large enough compared with its rolling variance.

## Execution style

This is mostly a passive strategy. It prefers to quote just inside the spread when:

- the spread is wide enough,
- the estimated quote quality is acceptable,
- inventory is still under control,
- and the product is not in cooldown after a bad run.

That matters because a lot of replay PnL in Prosperity can disappear if you turn a decent model into an overly eager taker.

## Risk controls

The bot includes a few practical controls that were important in my Round 5 iteration loop:

- position limits capped at `10` per product,
- category-level inventory awareness, not just single-product inventory,
- per-product cooldown after losses or large drawdowns,
- flattening near the end of the day (`timestamp >= 990000`),
- compressed `traderData` state so the persistent state stays safely under platform limits.

## Notes on the local data

The local dataset snapshot available in this folder contains:

- `prices_round_5_day_2.csv`
- `prices_round_5_day_3.csv`
- `prices_round_5_day_4.csv`
- matching trade files for days 2 to 4

So this write-up is based on the visible local replay data in this workspace, not a full all-days archive.

## Summary

If I had to summarize the Round 5 approach in one sentence: it is a hybrid of market making and statistical arbitrage, where fair value is learned online from order books, product-family structure, and a few explicit basket identities, while risk is controlled through inventory-aware quoting and drawdown-based throttling.
