
class SkipEvent(Exception):
    """Событие не требует обработки."""


def handle_payment_succeeded(payload, attempt):
    """
    Имитация обработки успешного платежа.

    simulate_failures позволяет управлять
    количеством искусственных ошибок.
    """

    failures = payload.get("simulate_failures", 0)

    if attempt <= failures:
        raise RuntimeError(
            f"Simulated payment processing error "
            f"on attempt {attempt}"
        )

    print(
        f"Payment processed successfully: "
        f"{payload}"
    )


def process_event(event_type, payload, attempt):
    """Выбирает обработчик по типу события."""

    handlers = {
        "payment_succeeded": handle_payment_succeeded,
    }

    handler = handlers.get(event_type)

    if handler is None:
        raise SkipEvent(
            f"Unknown event type: {event_type}"
        )

    handler(payload, attempt)
