from decimal import Decimal

from app.utils.yield_metrics import calculate_yield_metrics


def test_yield_metrics_normal_low_risk():
    m = calculate_yield_metrics(
        berat_lapangan_kg=Decimal("5.0"),
        berat_received_kg=Decimal("5.0"),
        berat_karantina_kg=Decimal("4.9"),
        berat_final_kg=Decimal("4.8"),
        kadar_air_pct=Decimal("15.0"),
    )
    assert m["risk_level"] == "LOW"
    assert "high_moisture" not in m["flags_json"]
    assert m["yield_pct"] == Decimal("96.000")


def test_high_moisture_sets_high_risk():
    m = calculate_yield_metrics(
        berat_lapangan_kg=Decimal("5.0"),
        berat_received_kg=Decimal("5.0"),
        berat_karantina_kg=Decimal("4.95"),
        berat_final_kg=Decimal("4.9"),
        kadar_air_pct=Decimal("18.0"),
    )
    assert m["risk_level"] == "HIGH"
    assert "high_moisture" in m["flags_json"]


def test_arrival_weight_higher_medium_risk():
    m = calculate_yield_metrics(
        berat_lapangan_kg=Decimal("5.0"),
        berat_received_kg=Decimal("5.2"),
        berat_karantina_kg=Decimal("5.1"),
        berat_final_kg=Decimal("5.0"),
    )
    assert m["risk_level"] == "MEDIUM"
    assert "arrival_weight_higher_than_field" in m["flags_json"]


def test_high_quarantine_shrink_flag():
    m = calculate_yield_metrics(
        berat_lapangan_kg=Decimal("10.0"),
        berat_received_kg=Decimal("10.0"),
        berat_karantina_kg=Decimal("9.5"),
    )
    assert "high_quarantine_shrink" in m["flags_json"]
    assert m["susut_received_to_quarantine_pct"] == Decimal("5.000")


def test_high_total_shrink_high_risk():
    m = calculate_yield_metrics(
        berat_lapangan_kg=Decimal("10.0"),
        berat_final_kg=Decimal("9.4"),
    )
    assert m["risk_level"] == "HIGH"
    assert "high_total_shrink" in m["flags_json"]
