# AGENTS.md

## Project overview
This service owns commerce state outside the UI. It stores cart, saved items, compare items, orders, order items, shipping snapshots, customer analytics, behavior-source export, and legacy order import.

## Goals
- Keep cart/checkout/order/shipping logic stable behind internal APIs.
- Preserve snapshot-based order history so old catalog data is not required at read time.

## Coding rules
- Keep `order_service` API-focused and internal-only by default.
- Reuse helpers inside the `orders` app before adding new layers.
- Preserve payment status and shipping status as separate concepts.
- Keep MySQL bootstrap aligned with Docker healthchecks.
- Keep MySQL bootstrap able to reconcile reused Docker volumes for `order_db` without manual volume deletion.
- Keep internal APIs protected with `ORDER_SERVICE_INTERNAL_KEY`; do not rely on host-published access.
- Keep legacy import logic compatible with `user_service`'s `LegacyUserMapping`.

## Testing
- Run relevant tests with `python manage.py test orders`.
- Verify cart/saved/compare, checkout with shipping data, pay order, staff shipping update, analytics, and legacy import helpers when touched.

## Dependencies
- Prefer Django, DRF, `requests`, and PyMySQL before adding new libraries.

## Output expectations
- Explain what changed.
- List touched files.
- Mention tradeoffs or remaining risks.
- Note what you verified.
