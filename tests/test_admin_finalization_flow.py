from app.repositories.inventory_repository import InventoryRepository
from tests.conftest import auth_header, new_uuid, sha256_hex
from tests.test_mobile_batch_flow import _batch_payload


def _full_mobile_pipeline(client, seed_users, mobile_token, dummy_jpeg) -> str:
    payload = _batch_payload(seed_users["device_id"])
    batch_uuid = payload["batch_uuid"]
    client.post("/api/mobile/batches", json=payload, headers=auth_header(mobile_token))
    for pt in ["UTUH", "CLOSE_UP_SERAT", "AREA_KOTORAN", "SAMPING"]:
        content = dummy_jpeg
        client.post(
            f"/api/mobile/batches/{batch_uuid}/photos",
            files={"file": ("sop.jpg", content, "image/jpeg")},
            data={
                "file_type": "SOP_PHOTO",
                "photo_type": pt,
                "sha256": sha256_hex(content),
            },
            headers=auth_header(mobile_token),
        )
    client.post(f"/api/mobile/batches/{batch_uuid}/submit", headers=auth_header(mobile_token))
    return batch_uuid


def test_admin_login(client, seed_users, admin_token):
    r = client.get("/api/auth/me", headers=auth_header(admin_token))
    assert r.status_code == 200
    assert r.json()["role"] == "ADMIN"


def test_admin_full_flow_creates_inventory_only_after_finalize(
    client, db, seed_users, mobile_token, admin_token, dummy_jpeg
):
    batch_uuid = _full_mobile_pipeline(client, seed_users, mobile_token, dummy_jpeg)
    headers = auth_header(admin_token)
    inv_repo = InventoryRepository(db)

    assert len(inv_repo.list_by_batch(batch_uuid)) == 0

    assert client.post(f"/api/admin/batches/{batch_uuid}/receive", headers=headers).status_code == 200
    assert (
        client.post(f"/api/admin/batches/{batch_uuid}/move-to-quarantine", headers=headers).status_code
        == 200
    )
    assert len(inv_repo.list_by_batch(batch_uuid)) == 0

    reweigh = {
        "gross_weight_kg": "1.300",
        "tare_weight_kg": "0.100",
        "net_weight_kg": "1.200",
        "shrinkage_kg": "0.050",
    }
    assert (
        client.post(f"/api/admin/batches/{batch_uuid}/reweigh", json=reweigh, headers=headers).status_code
        == 200
    )
    assert len(inv_repo.list_by_batch(batch_uuid)) == 0

    regrade = {
        "items": [
            {"grade_type": "MANGKUK", "weight_kg": "1.000"},
            {"grade_type": "SUDUT", "weight_kg": "0.200"},
        ]
    }
    assert (
        client.post(f"/api/admin/batches/{batch_uuid}/regrade", json=regrade, headers=headers).status_code
        == 200
    )
    assert len(inv_repo.list_by_batch(batch_uuid)) == 0

    fin = client.post(f"/api/admin/batches/{batch_uuid}/finalize", headers=headers)
    assert fin.status_code == 200
    assert fin.json()["status"] == "FINALIZED"

    lots = inv_repo.list_by_batch(batch_uuid)
    assert len(lots) >= 1
    assert all(lot.status.value == "VERIFIED" for lot in lots)

    detail = client.get(f"/api/admin/batches/{batch_uuid}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "FINALIZED"
    assert len(detail.json()["inventory_lots"]) >= 1
