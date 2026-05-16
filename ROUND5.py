from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

try:
    from datamodel import Order, OrderDepth, TradingState
except Exception:
    class Order:
        def __init__(self, symbol: str, price: int, quantity: int) -> None:
            self.symbol = symbol
            self.price = price
            self.quantity = quantity

        def __repr__(self) -> str:
            return f"Order({self.symbol}, {self.price}, {self.quantity})"

    class OrderDepth:
        buy_orders: Dict[int, int]
        sell_orders: Dict[int, int]

    class TradingState:
        traderData: str
        timestamp: int
        order_depths: Dict[str, OrderDepth]
        own_trades: Dict[str, List[Any]]
        market_trades: Dict[str, List[Any]]
        position: Dict[str, int]


Product = str


LIMIT = 10
MAX_STATE_CHARS = 45000
PEBBLE_SUM = 50000.0

IGNITH_PRODUCTS = [
    "AMETHYSTS",
    "STARFRUIT",
    "ORCHIDS",
    "CHOCOLATE",
    "STRAWBERRIES",
    "ROSES",
    "GIFT_BASKET",
    "COCONUT",
    "COCONUT_COUPON",
]

BASKET_WEIGHTS = {
    "CHOCOLATE": 4,
    "STRAWBERRIES": 6,
    "ROSES": 1,
}
IGNITH_SPECIAL_PRODUCTS = {
    "AMETHYSTS",
    "STARFRUIT",
    "CHOCOLATE",
    "STRAWBERRIES",
    "ROSES",
    "GIFT_BASKET",
}


GROUPS: Dict[str, List[Product]] = {
    "GALAXY": [
        "GALAXY_SOUNDS_DARK_MATTER",
        "GALAXY_SOUNDS_BLACK_HOLES",
        "GALAXY_SOUNDS_PLANETARY_RINGS",
        "GALAXY_SOUNDS_SOLAR_WINDS",
        "GALAXY_SOUNDS_SOLAR_FLAMES",
    ],
    "SLEEP": [
        "SLEEP_POD_SUEDE",
        "SLEEP_POD_LAMB_WOOL",
        "SLEEP_POD_POLYESTER",
        "SLEEP_POD_NYLON",
        "SLEEP_POD_COTTON",
    ],
    "MICROCHIP": [
        "MICROCHIP_CIRCLE",
        "MICROCHIP_OVAL",
        "MICROCHIP_SQUARE",
        "MICROCHIP_RECTANGLE",
        "MICROCHIP_TRIANGLE",
    ],
    "PEBBLES": [
        "PEBBLES_XS",
        "PEBBLES_S",
        "PEBBLES_M",
        "PEBBLES_L",
        "PEBBLES_XL",
    ],
    "ROBOT": [
        "ROBOT_VACUUMING",
        "ROBOT_MOPPING",
        "ROBOT_DISHES",
        "ROBOT_LAUNDRY",
        "ROBOT_IRONING",
    ],
    "UV": [
        "UV_VISOR_YELLOW",
        "UV_VISOR_AMBER",
        "UV_VISOR_ORANGE",
        "UV_VISOR_RED",
        "UV_VISOR_MAGENTA",
    ],
    "TRANSLATOR": [
        "TRANSLATOR_SPACE_GRAY",
        "TRANSLATOR_ASTRO_BLACK",
        "TRANSLATOR_ECLIPSE_CHARCOAL",
        "TRANSLATOR_GRAPHITE_MIST",
        "TRANSLATOR_VOID_BLUE",
    ],
    "PANEL": [
        "PANEL_1X2",
        "PANEL_2X2",
        "PANEL_1X4",
        "PANEL_2X4",
        "PANEL_4X4",
    ],
    "OXYGEN": [
        "OXYGEN_SHAKE_MORNING_BREATH",
        "OXYGEN_SHAKE_EVENING_BREATH",
        "OXYGEN_SHAKE_MINT",
        "OXYGEN_SHAKE_CHOCOLATE",
        "OXYGEN_SHAKE_GARLIC",
    ],
    "SNACK": [
        "SNACKPACK_CHOCOLATE",
        "SNACKPACK_VANILLA",
        "SNACKPACK_PISTACHIO",
        "SNACKPACK_STRAWBERRY",
        "SNACKPACK_RASPBERRY",
    ],
    "IGNITH": IGNITH_PRODUCTS,
}


PRODUCT_TO_GROUP: Dict[Product, str] = {
    product: group for group, products in GROUPS.items() for product in products
}


ALL_ROUND5_PRODUCTS = set(PRODUCT_TO_GROUP.keys())


HIGH_RISK_PRODUCTS = {
    "PANEL_1X2",
    "SLEEP_POD_LAMB_WOOL",
    "PEBBLES_XS",
    "PEBBLES_M",
    "TRANSLATOR_SPACE_GRAY",
    "TRANSLATOR_ECLIPSE_CHARCOAL",
    "TRANSLATOR_GRAPHITE_MIST",
    "OXYGEN_SHAKE_MINT",
    "GALAXY_SOUNDS_DARK_MATTER",
    "MICROCHIP_RECTANGLE",
    "ROBOT_MOPPING",
    "UV_VISOR_MAGENTA",
}


DISABLED_PRODUCTS = set()


CAUTION_PRODUCTS = {
    "PANEL_4X4",
    "PEBBLES_L",
}


IGNITH_PASSIVE_PRODUCTS = {
    "ORCHIDS",
    "COCONUT",
    "COCONUT_COUPON",
}


def median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n % 2:
        return ordered[n // 2]
    return 0.5 * (ordered[n // 2 - 1] + ordered[n // 2])


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def group_for(product: Product) -> Optional[str]:
    if product in PRODUCT_TO_GROUP:
        return PRODUCT_TO_GROUP[product]
    if product.startswith("IGNITH_"):
        return "IGNITH"
    return None


def is_supported_product(product: Product) -> bool:
    return group_for(product) is not None


class Trader:
    def bid(self) -> int:
        return 15

    def run(self, state: TradingState):
        data = self._load_state(state.traderData)
        product_state: Dict[str, Dict[str, float]] = data.setdefault("p", {})
        cash: Dict[str, float] = data.setdefault("c", {})
        peak: Dict[str, float] = data.setdefault("pk", {})
        cooldown: Dict[str, int] = data.setdefault("cd", {})
        basket_state: Dict[str, float] = data.setdefault("basket", {})
        pair_state: Dict[str, float] = data.setdefault("pair", {})
        mark_state: Dict[str, Any] = data.setdefault("marks", {})
        learned: Dict[str, float] = data.setdefault("learn", {})

        mids: Dict[str, float] = {}
        books: Dict[str, Tuple[int, int, int, int, int, int]] = {}
        for product, depth in state.order_depths.items():
            if not is_supported_product(product):
                continue
            book = self._book(depth)
            if book is None:
                continue
            best_bid, bid_vol, best_ask, ask_vol, bid_total, ask_total = book
            mids[product] = 0.5 * (best_bid + best_ask)
            books[product] = (best_bid, bid_vol, best_ask, ask_vol, bid_total, ask_total)

        group_center: Dict[str, Optional[float]] = {}
        category_position: Dict[str, int] = {}
        for group, products in GROUPS.items():
            group_center[group] = median([mids[p] for p in products if p in mids])
            category_position[group] = sum(int(state.position.get(p, 0)) for p in products)

        self._update_mark_signals(state, mark_state, books, mids)

        synthetic_fair: Dict[str, float] = {}
        pebbles = GROUPS["PEBBLES"]
        if all(product in mids for product in pebbles):
            pebble_total = sum(mids[product] for product in pebbles)
            pebble_target = self._learn_constant(learned, "pebble_sum", pebble_total, PEBBLE_SUM, 0.006)
            for product in pebbles:
                synthetic_fair[product] = pebble_target - (pebble_total - mids[product])

        self._update_cash_from_trades(state, cash, mids)
        result: Dict[str, List[Order]] = {}

        for product, book in books.items():
            if product not in product_state:
                product_state[product] = self._fresh_state(mids[product], book[2] - book[0])

        for product, book in books.items():
            position = int(state.position.get(product, 0))
            best_bid, bid_vol, best_ask, ask_vol, bid_total, ask_total = book
            mid = mids[product]
            spread = best_ask - best_bid
            pstate = product_state[product]
            mark_pnl = cash.get(product, 0.0) + position * mid
            peak[product] = max(peak.get(product, mark_pnl), mark_pnl)

            if cooldown.get(product, 0) > 0:
                cooldown[product] -= 1
            cooldown_vol = math.sqrt(max(1.0, pstate["var"]))
            loss_floor = -(6500.0 + 240.0 * cooldown_vol)
            drawdown_buffer = 9500.0 + 180.0 * cooldown_vol
            if mark_pnl < loss_floor or mark_pnl < peak[product] - drawdown_buffer:
                cooldown[product] = max(cooldown.get(product, 0), 120)

            orders: List[Order] = []
            if product in DISABLED_PRODUCTS:
                if position != 0:
                    self._flatten(product, orders, position, best_bid, best_ask)
                    result[product] = orders
                continue

            if state.timestamp >= 990000:
                self._flatten(product, orders, position, best_bid, best_ask)
                result[product] = orders
                continue

            if product in IGNITH_SPECIAL_PRODUCTS:
                continue

            vol = math.sqrt(max(1.0, pstate["var"]))
            quality = spread / (vol + 1.0)
            age = int(pstate.get("n", 0))
            min_spread = 6
            min_quality = 0.0
            inventory_cap = 8
            size_cap = 2

            if product == "PANEL_4X4":
                min_spread = 12
                min_quality = 1.10
                inventory_cap = 2
                size_cap = 1
            elif product in CAUTION_PRODUCTS:
                min_spread = 10
                min_quality = 0.80
                inventory_cap = 4
                size_cap = 1
            elif product in HIGH_RISK_PRODUCTS:
                min_spread = 10
                min_quality = 1.00
                inventory_cap = 3
                size_cap = 1
            elif product in IGNITH_PASSIVE_PRODUCTS:
                min_spread = 4
                min_quality = 0.85
                inventory_cap = 2
                size_cap = 1

            if age < 5:
                min_quality += 0.45
                inventory_cap = min(inventory_cap, 2)
                size_cap = 1
            elif age < 25 and product in HIGH_RISK_PRODUCTS:
                min_quality += 0.25
                inventory_cap = min(inventory_cap, 2)

            if cooldown.get(product, 0) > 0:
                min_spread += 2
                min_quality += 0.60
                size_cap = 1
                inventory_cap = min(inventory_cap, 3)

            group = group_for(product)
            if group is not None and group != "IGNITH":
                sector_position = category_position.get(group, position)
            else:
                sector_position = position
            fair = self._fair_value(
                product,
                mid,
                spread,
                bid_total,
                ask_total,
                pstate,
                group_center,
                synthetic_fair,
                mark_state,
            )

            if spread >= min_spread and quality >= min_quality:
                self._quote_market(
                    product,
                    orders,
                    position,
                    sector_position,
                    best_bid,
                    best_ask,
                    mid,
                    fair,
                    spread,
                    vol,
                    quality,
                    inventory_cap,
                    size_cap,
                )

            if orders:
                result[product] = orders

        if state.timestamp < 990000:
            self._trade_amethysts(result, state.position, books, cooldown, learned)
            self._trade_starfruit(result, state.position, books, product_state, cooldown)
            self._trade_gift_basket(result, state.position, books, mids, basket_state, cooldown)
            self._trade_snack_pair(result, state.position, books, mids, pair_state, cooldown)

        self._update_product_state(product_state, books, mids, group_center, synthetic_fair)
        data["t"] = int(state.timestamp)
        trader_data = self._dump_state(data)
        return result, 0, trader_data

    def _load_state(self, trader_data: str) -> Dict[str, Any]:
        if not trader_data:
            return {"p": {}, "c": {}, "pk": {}, "cd": {}, "t": 0}
        try:
            data = json.loads(trader_data)
            if isinstance(data, dict):
                data.setdefault("p", {})
                data.setdefault("c", {})
                data.setdefault("pk", {})
                data.setdefault("cd", {})
                return data
        except Exception:
            pass
        return {"p": {}, "c": {}, "pk": {}, "cd": {}, "t": 0}

    def _dump_state(self, data: Dict[str, Any]) -> str:
        text = json.dumps(data, separators=(",", ":"))
        if len(text) <= MAX_STATE_CHARS:
            return text
        compact = json.loads(text)
        for pstate in compact.get("p", {}).values():
            history = pstate.get("rh")
            if isinstance(history, list) and len(history) > 40:
                pstate["rh"] = history[-40:]
        text = json.dumps(compact, separators=(",", ":"))
        if len(text) <= MAX_STATE_CHARS:
            return text
        for pstate in compact.get("p", {}).values():
            pstate.pop("rh", None)
        text = json.dumps(compact, separators=(",", ":"))
        if len(text) <= MAX_STATE_CHARS:
            return text
        minimal = {"p": compact.get("p", {}), "t": compact.get("t", 0)}
        return json.dumps(minimal, separators=(",", ":"))

    def _fresh_state(self, mid: float, spread: int) -> Dict[str, float]:
        return {
            "last": mid,
            "fast": mid,
            "slow": mid,
            "var": 64.0,
            "sp": float(max(1, spread)),
            "res": 0.0,
            "rv": 100.0,
            "rh": [],
            "n": 0,
        }

    def _book(self, depth: OrderDepth) -> Optional[Tuple[int, int, int, int, int, int]]:
        if not depth.buy_orders or not depth.sell_orders:
            return None
        best_bid = max(depth.buy_orders)
        best_ask = min(depth.sell_orders)
        bid_vol = max(0, int(depth.buy_orders[best_bid]))
        ask_vol = abs(int(depth.sell_orders[best_ask]))
        bid_total = sum(max(0, int(q)) for q in depth.buy_orders.values())
        ask_total = sum(abs(int(q)) for q in depth.sell_orders.values())
        if bid_vol <= 0 or ask_vol <= 0 or best_bid >= best_ask:
            return None
        return best_bid, bid_vol, best_ask, ask_vol, bid_total, ask_total

    def _learn_constant(
        self,
        learned: Dict[str, float],
        key: str,
        observation: float,
        default: float,
        rate: float,
    ) -> float:
        current = float(learned.get(key, default))
        current = (1.0 - rate) * current + rate * observation
        learned[key] = current
        return current

    def _is_mark(self, name: Any) -> bool:
        return "MARK" in str(name).upper()

    def _update_mark_signals(
        self,
        state: TradingState,
        mark_state: Dict[str, Any],
        books: Dict[str, Tuple[int, int, int, int, int, int]],
        mids: Dict[str, float],
    ) -> None:
        product_signal: Dict[str, float] = mark_state.setdefault("p", {})
        for product in list(product_signal):
            product_signal[product] *= 0.82
            if abs(product_signal[product]) < 0.05:
                product_signal.pop(product, None)

        market_trades = getattr(state, "market_trades", {}) or {}
        for product, trades in market_trades.items():
            if product not in books or product not in mids:
                continue
            best_bid, _, best_ask, _, _, _ = books[product]
            spread = max(1.0, best_ask - best_bid)
            for trade in trades:
                buyer = getattr(trade, "buyer", "")
                seller = getattr(trade, "seller", "")
                qty = abs(int(getattr(trade, "quantity", 0)))
                if qty <= 0:
                    continue
                signed = 0
                if self._is_mark(buyer) and not self._is_mark(seller):
                    signed = qty
                elif self._is_mark(seller) and not self._is_mark(buyer):
                    signed = -qty
                if signed == 0:
                    continue
                price = float(getattr(trade, "price", mids[product]))
                urgency = 1.0 + min(2.0, abs(price - mids[product]) / spread)
                product_signal[product] = product_signal.get(product, 0.0) + signed * urgency

    def _mark_bias(self, product: Product, mark_state: Dict[str, Any]) -> float:
        product_signal = mark_state.get("p", {})
        signal = float(product_signal.get(product, 0.0))
        group = group_for(product)
        if group is None or group == "IGNITH":
            return clamp(0.25 * signal, -4.0, 4.0)
        peers = [p for p in GROUPS[group] if p in product_signal]
        if not peers:
            return 0.0
        peer_mean = sum(float(product_signal[p]) for p in peers) / len(peers)
        relative_signal = signal - peer_mean
        return clamp(0.45 * relative_signal + 0.10 * signal, -6.0, 6.0)

    def _append_limited(
        self,
        result: Dict[str, List[Order]],
        positions: Dict[str, int],
        product: Product,
        price: int,
        quantity: int,
    ) -> None:
        if quantity == 0:
            return
        existing = result.setdefault(product, [])
        position = int(positions.get(product, 0))
        if quantity > 0:
            planned_buy = sum(order.quantity for order in existing if order.quantity > 0)
            room = max(0, LIMIT - position - planned_buy)
            quantity = min(quantity, room)
        else:
            planned_sell = sum(-order.quantity for order in existing if order.quantity < 0)
            room = max(0, LIMIT + position - planned_sell)
            quantity = -min(-quantity, room)
        if quantity:
            existing.append(Order(product, int(price), int(quantity)))

    def _trade_fair_value(
        self,
        result: Dict[str, List[Order]],
        positions: Dict[str, int],
        product: Product,
        book: Tuple[int, int, int, int, int, int],
        fair: float,
        edge: float,
        passive_size: int = 1,
    ) -> None:
        best_bid, bid_vol, best_ask, ask_vol, _, _ = book
        if best_ask <= fair - edge:
            self._append_limited(result, positions, product, best_ask, min(ask_vol, 2))
        if best_bid >= fair + edge:
            self._append_limited(result, positions, product, best_bid, -min(bid_vol, 2))

        if best_ask - best_bid >= 3:
            bid_price = min(best_bid + 1, int(math.floor(fair - 1)))
            ask_price = max(best_ask - 1, int(math.ceil(fair + 1)))
            if bid_price < fair:
                self._append_limited(result, positions, product, bid_price, passive_size)
            if ask_price > fair:
                self._append_limited(result, positions, product, ask_price, -passive_size)

    def _trade_amethysts(
        self,
        result: Dict[str, List[Order]],
        positions: Dict[str, int],
        books: Dict[str, Tuple[int, int, int, int, int, int]],
        cooldown: Dict[str, int],
        learned: Dict[str, float],
    ) -> None:
        book = books.get("AMETHYSTS")
        if book is None or cooldown.get("AMETHYSTS", 0) > 0:
            return
        best_bid, _, best_ask, _, _, _ = book
        mid = 0.5 * (best_bid + best_ask)
        current = float(learned.get("amethysts_fair", 10000.0))
        if abs(mid - current) < 60:
            current = self._learn_constant(learned, "amethysts_fair", mid, 10000.0, 0.002)
        self._trade_fair_value(result, positions, "AMETHYSTS", book, current, 2.0, 2)

    def _trade_starfruit(
        self,
        result: Dict[str, List[Order]],
        positions: Dict[str, int],
        books: Dict[str, Tuple[int, int, int, int, int, int]],
        product_state: Dict[str, Dict[str, float]],
        cooldown: Dict[str, int],
    ) -> None:
        book = books.get("STARFRUIT")
        if book is None or cooldown.get("STARFRUIT", 0) > 0:
            return
        best_bid, _, best_ask, _, _, _ = book
        mid = 0.5 * (best_bid + best_ask)
        pstate = product_state.setdefault("STARFRUIT", self._fresh_state(mid, best_ask - best_bid))
        vol = math.sqrt(max(1.0, pstate["var"]))
        fair = pstate["fast"] + clamp(0.20 * (pstate["fast"] - pstate["slow"]), -3.0, 3.0)
        self._trade_fair_value(result, positions, "STARFRUIT", book, fair, max(2.0, 0.35 * vol), 1)

    def _trade_gift_basket(
        self,
        result: Dict[str, List[Order]],
        positions: Dict[str, int],
        books: Dict[str, Tuple[int, int, int, int, int, int]],
        mids: Dict[str, float],
        basket_state: Dict[str, float],
        cooldown: Dict[str, int],
    ) -> None:
        required = ["GIFT_BASKET", "CHOCOLATE", "STRAWBERRIES", "ROSES"]
        if any(product not in books or product not in mids for product in required):
            return
        if any(cooldown.get(product, 0) > 0 for product in required):
            return

        synthetic = sum(BASKET_WEIGHTS[product] * mids[product] for product in BASKET_WEIGHTS)
        residual = mids["GIFT_BASKET"] - synthetic
        if "ema" not in basket_state:
            basket_state["ema"] = residual
            basket_state["var"] = 400.0
            basket_state["n"] = 0

        residual_vol = math.sqrt(max(1.0, basket_state.get("var", 400.0)))
        threshold = max(18.0, 1.35 * residual_vol)

        sell_basket_edge = books["GIFT_BASKET"][0] - sum(
            BASKET_WEIGHTS[product] * books[product][2] for product in BASKET_WEIGHTS
        ) - basket_state["ema"]
        buy_basket_edge = books["GIFT_BASKET"][2] - sum(
            BASKET_WEIGHTS[product] * books[product][0] for product in BASKET_WEIGHTS
        ) - basket_state["ema"]

        if basket_state.get("n", 0) >= 30 and sell_basket_edge > threshold:
            qty = self._basket_package_capacity(positions, sell_basket=True)
            if qty > 0:
                self._append_limited(result, positions, "GIFT_BASKET", books["GIFT_BASKET"][0], -qty)
                for product, weight in BASKET_WEIGHTS.items():
                    self._append_limited(result, positions, product, books[product][2], qty * weight)
        elif basket_state.get("n", 0) >= 30 and buy_basket_edge < -threshold:
            qty = self._basket_package_capacity(positions, sell_basket=False)
            if qty > 0:
                self._append_limited(result, positions, "GIFT_BASKET", books["GIFT_BASKET"][2], qty)
                for product, weight in BASKET_WEIGHTS.items():
                    self._append_limited(result, positions, product, books[product][0], -qty * weight)

        diff = residual - basket_state["ema"]
        basket_state["ema"] = 0.985 * basket_state["ema"] + 0.015 * residual
        basket_state["var"] = 0.97 * basket_state.get("var", 400.0) + 0.03 * diff * diff
        basket_state["n"] = basket_state.get("n", 0) + 1

    def _basket_package_capacity(self, positions: Dict[str, int], sell_basket: bool) -> int:
        if sell_basket:
            capacity = LIMIT + int(positions.get("GIFT_BASKET", 0))
            for product, weight in BASKET_WEIGHTS.items():
                capacity = min(capacity, (LIMIT - int(positions.get(product, 0))) // weight)
        else:
            capacity = LIMIT - int(positions.get("GIFT_BASKET", 0))
            for product, weight in BASKET_WEIGHTS.items():
                capacity = min(capacity, (LIMIT + int(positions.get(product, 0))) // weight)
        return max(0, min(1, capacity))

    def _trade_snack_pair(
        self,
        result: Dict[str, List[Order]],
        positions: Dict[str, int],
        books: Dict[str, Tuple[int, int, int, int, int, int]],
        mids: Dict[str, float],
        pair_state: Dict[str, float],
        cooldown: Dict[str, int],
    ) -> None:
        first = "SNACKPACK_CHOCOLATE"
        second = "SNACKPACK_VANILLA"
        if first not in books or second not in books or first not in mids or second not in mids:
            return
        if cooldown.get(first, 0) > 0 or cooldown.get(second, 0) > 0:
            return

        pair_value = mids[first] - mids[second]
        if "ema" not in pair_state:
            pair_state["ema"] = pair_value
            pair_state["var"] = 100.0
            pair_state["n"] = 0

        pair_vol = math.sqrt(max(1.0, pair_state.get("var", 100.0)))
        threshold = max(60.0, 1.75 * pair_vol)

        high_edge = books[first][0] - books[second][2] - pair_state["ema"]
        low_edge = books[first][2] - books[second][0] - pair_state["ema"]

        if pair_state.get("n", 0) >= 40 and high_edge > threshold:
            self._append_limited(result, positions, first, books[first][0], -1)
            self._append_limited(result, positions, second, books[second][2], 1)
        elif pair_state.get("n", 0) >= 40 and low_edge < -threshold:
            self._append_limited(result, positions, first, books[first][2], 1)
            self._append_limited(result, positions, second, books[second][0], -1)

        diff = pair_value - pair_state["ema"]
        pair_state["ema"] = 0.985 * pair_state["ema"] + 0.015 * pair_value
        pair_state["var"] = 0.97 * pair_state.get("var", 100.0) + 0.03 * diff * diff
        pair_state["n"] = pair_state.get("n", 0) + 1

    def _fair_value(
        self,
        product: Product,
        mid: float,
        spread: int,
        bid_total: int,
        ask_total: int,
        pstate: Dict[str, float],
        group_center: Dict[str, Optional[float]],
        synthetic_fair: Dict[str, float],
        mark_state: Dict[str, Any],
    ) -> float:
        fair = mid
        trend = pstate["fast"] - pstate["slow"]
        fair += clamp(0.12 * trend, -4.0, 4.0)
        mark_bias = self._mark_bias(product, mark_state)

        if product in synthetic_fair:
            synthetic_signal = synthetic_fair[product] - mid
            residual_vol = math.sqrt(max(1.0, pstate["rv"]))
            if abs(synthetic_signal) > max(spread, 2.0 * residual_vol):
                fair = synthetic_fair[product]
            else:
                fair += clamp(0.20 * synthetic_signal, -4.0, 4.0)
            imbalance = (bid_total - ask_total) / max(1.0, bid_total + ask_total)
            fair += mark_bias
            fair += clamp(-0.12 * imbalance * spread, -2.0, 2.0)
            return fair

        group = group_for(product)
        if group == "IGNITH":
            group = None
        center = group_center.get(group) if group is not None else None
        if center is not None:
            group_fair = center + pstate["res"]
            group_signal = group_fair - mid
            residual_vol = math.sqrt(max(1.0, pstate["rv"]))
            if abs(group_signal) > max(spread, 2.0 * residual_vol):
                fair += clamp(0.55 * group_signal, -14.0, 14.0)
            elif abs(group_signal) > 0.75 * spread:
                fair += clamp(0.15 * group_signal, -3.0, 3.0)

        imbalance = (bid_total - ask_total) / max(1.0, bid_total + ask_total)
        fair += mark_bias
        fair += clamp(-0.18 * imbalance * spread, -3.0, 3.0)
        return fair

    def _quote_market(
        self,
        product: Product,
        orders: List[Order],
        position: int,
        category_position: int,
        best_bid: int,
        best_ask: int,
        mid: float,
        fair: float,
        spread: int,
        vol: float,
        quality: float,
        inventory_cap: int,
        size_cap: int,
    ) -> None:
        unit = max(4.0, 0.65 * vol, 0.45 * spread)

        size = min(2, size_cap)
        if quality > 1.15:
            size = 2
        if quality > 1.85:
            size = size_cap
        size = max(1, min(size, size_cap))

        bid = best_bid + 1
        ask = best_ask - 1
        if category_position > 2:
            ask -= min(3, max(1, (category_position + 1) // 4))
            bid -= min(2, max(0, category_position // 5))
        elif category_position < -2:
            bid += min(3, max(1, (-category_position + 1) // 4))
            ask += min(2, max(0, (-category_position) // 5))

        if position >= inventory_cap:
            bid -= 2
        elif position <= -inventory_cap:
            ask += 2

        if bid >= ask:
            bid = best_bid
            ask = best_ask

        buy_room = max(0, LIMIT - position)
        sell_room = max(0, LIMIT + position)
        neutral_wide = abs(fair - mid) < 0.50 * spread

        buy_ok = buy_room > 0 and position < inventory_cap and bid <= fair - 1
        sell_ok = sell_room > 0 and position > -inventory_cap and ask >= fair + 1
        if neutral_wide:
            buy_ok = buy_room > 0 and position < inventory_cap
            sell_ok = sell_room > 0 and position > -inventory_cap
        if category_position >= LIMIT:
            buy_ok = False
        elif category_position <= -LIMIT:
            sell_ok = False

        if buy_ok:
            orders.append(Order(product, int(bid), min(size, buy_room)))
        if sell_ok:
            orders.append(Order(product, int(ask), -min(size, sell_room)))

    def _flatten(
        self,
        product: Product,
        orders: List[Order],
        position: int,
        best_bid: int,
        best_ask: int,
    ) -> None:
        if position > 0:
            orders.append(Order(product, best_bid, -min(position, LIMIT)))
        elif position < 0:
            orders.append(Order(product, best_ask, min(-position, LIMIT)))

    def _update_residual_state(self, pstate: Dict[str, Any], residual: float) -> None:
        history = pstate.setdefault("rh", [])
        if not isinstance(history, list):
            history = []
            pstate["rh"] = history
        history.append(int(round(residual)))
        if len(history) > 100:
            del history[:-100]
        mean = sum(history) / len(history)
        variance = sum((value - mean) * (value - mean) for value in history) / max(1, len(history) - 1)
        pstate["res"] = mean
        pstate["rv"] = max(1.0, variance)

    def _update_product_state(
        self,
        product_state: Dict[str, Dict[str, float]],
        books: Dict[str, Tuple[int, int, int, int, int, int]],
        mids: Dict[str, float],
        group_center: Dict[str, Optional[float]],
        synthetic_fair: Dict[str, float],
    ) -> None:
        for product, mid in mids.items():
            best_bid, _, best_ask, _, _, _ = books[product]
            spread = best_ask - best_bid
            pstate = product_state.setdefault(product, self._fresh_state(mid, spread))
            ret = mid - pstate["last"]
            pstate["last"] = mid
            pstate["var"] = 0.94 * pstate["var"] + 0.06 * ret * ret
            pstate["fast"] = 0.85 * pstate["fast"] + 0.15 * mid
            pstate["slow"] = 0.98 * pstate["slow"] + 0.02 * mid
            pstate["sp"] = 0.90 * pstate["sp"] + 0.10 * spread
            pstate["n"] = pstate.get("n", 0) + 1

            if product in synthetic_fair:
                residual = mid - synthetic_fair[product]
                self._update_residual_state(pstate, residual)
                continue

            group = group_for(product)
            if group == "IGNITH":
                group = None
            center = group_center.get(group) if group is not None else None
            if center is not None:
                residual = mid - center
                self._update_residual_state(pstate, residual)

    def _update_cash_from_trades(
        self,
        state: TradingState,
        cash: Dict[str, float],
        mids: Dict[str, float],
    ) -> None:
        own_trades = getattr(state, "own_trades", {}) or {}
        for product, trades in own_trades.items():
            if not is_supported_product(product):
                continue
            for trade in trades:
                price = float(getattr(trade, "price", mids.get(product, 0.0)))
                qty = int(getattr(trade, "quantity", 0))
                buyer = str(getattr(trade, "buyer", ""))
                seller = str(getattr(trade, "seller", ""))
                signed_qty = 0
                if buyer.startswith("SUBMISSION"):
                    signed_qty = qty
                elif seller.startswith("SUBMISSION"):
                    signed_qty = -qty
                if signed_qty:
                    cash[product] = cash.get(product, 0.0) - signed_qty * price
