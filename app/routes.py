
from flask import Blueprint, current_app, jsonify, request

from app.services import create_event, get_statistics


main_bp = Blueprint("main", __name__)


@main_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Event Receiver is running"
    }), 200


@main_bp.route("/webhook", methods=["POST"])
def webhook():
    # Проверяем Content-Type.
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json"
        }), 415

    # Читаем JSON.
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a valid JSON object"
        }), 400

    # Проверяем обязательные поля.
    event_id = data.get("event_id")
    event_type = data.get("type")
    payload = data.get("payload")

    if not isinstance(event_id, str) or not event_id.strip():
        return jsonify({
            "error": "event_id must be a non-empty string"
        }), 400

    if not isinstance(event_type, str) or not event_type.strip():
        return jsonify({
            "error": "type must be a non-empty string"
        }), 400

    if not isinstance(payload, dict):
        return jsonify({
            "error": "payload must be a JSON object"
        }), 400

    # Сохраняем событие и создаём задачу.
    try:
        is_new = create_event(
            database_path=current_app.config["DATABASE"],
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )
    except Exception:
        current_app.logger.exception(
            "Failed to save webhook event"
        )

        return jsonify({
            "error": "Failed to save event"
        }), 500

    if not is_new:
        return jsonify({
            "status": "duplicate",
            "event_id": event_id,
        }), 200

    return jsonify({
        "status": "accepted",
        "event_id": event_id,
    }), 202



@main_bp.route("/stats", methods=["GET"])
def stats():
    statistics = get_statistics(
        database_path=current_app.config["DATABASE"]
    )
    return jsonify(statistics), 200
