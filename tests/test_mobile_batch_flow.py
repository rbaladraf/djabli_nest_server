from decimal import Decimal

from app.utils.hash_utils import sha256_hex
from app.utils.id_utils import new_uuid
from tests.conftest import auth_header


def _batch_payload(device_id: str, batch_uuid: str | None = None) -> dict:
    return {
        "batch_uuid": batch_uuid or new_uuid(),
        "batch_code": "DN-TEST-001",
        "device_id": device_id,
        "farmer": {
            "name": "Petani A",
            "location": "Sulawesi",
            "latitude": "1.23",
            "longitude": "124.45",
            "note": "catatan",
        },
        "deal_type": "KLASIFIKASI",
        "purchase_details": [
            {
                "item_type": "MANGKUK",
                "weight_kg": "1.200",
                "price_per_kg": "12000000",
                "subtotal": "14400000",
            }
        ],
        "payment": {"method": "CASH", "amount": "14400000", "note": ""},
        "costs": [{"cost_type": "TRANSPORT", "amount": "100000", "note": ""}],
    }


def test_mobile_create_submit_flow(client, seed_users, mobile_token, dummy_jpeg):
    device_id = seed_users["device_id"]
    payload = _batch_payload(device_id)
    batch_uuid = payload["batch_uuid"]

    r = client.post(
        "/api/mobile/batches",
        json=payload,
        headers=auth_header(mobile_token),
    )
    assert r.status_code == 200
    assert r.json()["batch_uuid"] == batch_uuid

    photo_types = ["UTUH", "CLOSE_UP_SERAT", "AREA_KOTORAN", "SAMPING"]
    for pt in photo_types:
        content = dummy_jpeg
        files = {"file": ("sop.jpg", content, "image/jpeg")}
        data = {
            "file_type": "SOP_PHOTO",
            "photo_type": pt,
            "sha256": sha256_hex(content),
        }
        up = client.post(
            f"/api/mobile/batches/{batch_uuid}/photos",
            files=files,
            data=data,
            headers=auth_header(mobile_token),
        )
        assert up.status_code == 200, up.text

    submit = client.post(
        f"/api/mobile/batches/{batch_uuid}/submit",
        headers=auth_header(mobile_token),
    )
    assert submit.status_code == 200
    assert submit.json()["status"] == "UPLOADED"


def test_create_batch_idempotency(client, seed_users, mobile_token):
    device_id = seed_users["device_id"]
    payload = _batch_payload(device_id)
    headers = auth_header(mobile_token)
    r1 = client.post("/api/mobile/batches", json=payload, headers=headers)
    r2 = client.post("/api/mobile/batches", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["batch_uuid"] == r2.json()["batch_uuid"]
