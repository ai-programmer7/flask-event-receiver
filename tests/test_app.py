
def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_webhook_success(client):
    response = client.post(
        "/webhook",
        json={
            "event_id": "test-event-001",
            "type": "payment_succeeded",
            "payload": {
                "amount": 1500,
                "currency": "RUB"
            }
        }
    )

    assert response.status_code == 202
    assert response.json["status"] == "accepted"
    assert response.json["event_id"] == "test-event-001"



def test_webhook_duplicate(client):
    event = {
        "event_id": "duplicate-event-001",
        "type": "payment_succeeded",
        "payload": {
            "amount": 2000
        }
    }

    first_response = client.post("/webhook", json=event)
    second_response = client.post("/webhook", json=event)

    assert first_response.status_code == 202
    assert second_response.status_code == 200
    assert second_response.json["status"] == "duplicate"

    stats_response = client.get("/stats")

    assert stats_response.json["total_events"] == 1
    assert stats_response.json["total_tasks"] == 1



def test_webhook_invalid_data(client):
    # Отсутствует event_id
    response = client.post(
        "/webhook",
        json={
            "type": "payment_succeeded",
            "payload": {"amount": 1500}
        }
    )

    assert response.status_code == 400
    assert "error" in response.json


def test_webhook_invalid_content_type(client):
    response = client.post(
        "/webhook",
        data="not json",
        content_type="text/plain"
    )

    assert response.status_code == 415
    assert "error" in response.json



def test_stats(client):
    client.post(
        "/webhook",
        json={
            "event_id": "stats-event-001",
            "type": "payment_succeeded",
            "payload": {"amount": 3000}
        }
    )

    response = client.get("/stats")

    assert response.status_code == 200
    assert response.json["total_events"] == 1
    assert response.json["total_tasks"] == 1
    assert response.json["events_by_type"]["payment_succeeded"] == 1
    assert response.json["tasks_by_status"]["pending"] == 1
