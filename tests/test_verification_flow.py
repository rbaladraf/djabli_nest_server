from decimal import Decimal

from app.utils.yield_metrics import calculate_yield_metrics


def test_verification_endpoint_high_moisture_flag(client, seed_users, admin_token, mobile_token, dummy_jpeg):
    from tests.test_admin_finalization_flow import _full_mobile_pipeline

    batch_uuid = _full_mobile_pipeline(client, seed_users, mobile_token, dummy_jpeg)
    headers = {"Authorization": f"Bearer {admin_token}"}
    r = client.post(
        f"/api/admin/batches/{batch_uuid}/receive",
        json={"berat_received_kg": "5.0", "kadar_air_pct": "22.0"},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["verification"]["risk_level"] == "HIGH"
    assert "high_moisture" in body["verification"]["flags"]
