from decimal import Decimal
from typing import Any, Optional

from app.models.verification import RiskLevel

HIGH_QUARANTINE_SHRINK_THRESHOLD = Decimal("3.0")
HIGH_TOTAL_SHRINK_THRESHOLD = Decimal("5.0")
HIGH_MOISTURE_THRESHOLD = Decimal("18.0")


def _pct(numerator: Decimal, denominator: Decimal) -> Optional[Decimal]:
    if denominator <= 0:
        return None
    return (numerator / denominator * Decimal("100")).quantize(Decimal("0.001"))


def calculate_yield_metrics(
    *,
    berat_lapangan_kg: Decimal,
    berat_received_kg: Optional[Decimal] = None,
    berat_karantina_kg: Optional[Decimal] = None,
    berat_reweighing_kg: Optional[Decimal] = None,
    berat_final_kg: Optional[Decimal] = None,
    kadar_air_pct: Optional[Decimal] = None,
) -> dict[str, Any]:
    flags: list[str] = []

    susut_received_to_quarantine_pct: Optional[Decimal] = None
    if berat_received_kg is not None and berat_karantina_kg is not None:
        susut_received_to_quarantine_pct = _pct(
            berat_received_kg - berat_karantina_kg, berat_received_kg
        )
        if (
            susut_received_to_quarantine_pct is not None
            and susut_received_to_quarantine_pct > HIGH_QUARANTINE_SHRINK_THRESHOLD
        ):
            flags.append("high_quarantine_shrink")

    if berat_received_kg is not None and berat_received_kg > berat_lapangan_kg:
        flags.append("arrival_weight_higher_than_field")

    susut_lapangan_to_final_pct: Optional[Decimal] = None
    yield_pct: Optional[Decimal] = None
    if berat_final_kg is not None:
        final_weight = berat_final_kg
        susut_lapangan_to_final_pct = _pct(berat_lapangan_kg - final_weight, berat_lapangan_kg)
        yield_pct = _pct(final_weight, berat_lapangan_kg)
        if (
            susut_lapangan_to_final_pct is not None
            and susut_lapangan_to_final_pct > HIGH_TOTAL_SHRINK_THRESHOLD
        ):
            flags.append("high_total_shrink")

    if kadar_air_pct is not None and kadar_air_pct >= HIGH_MOISTURE_THRESHOLD:
        flags.append("high_moisture")

    risk_level = RiskLevel.LOW
    if "high_total_shrink" in flags or "high_moisture" in flags:
        risk_level = RiskLevel.HIGH
    elif "arrival_weight_higher_than_field" in flags or "high_quarantine_shrink" in flags:
        risk_level = RiskLevel.MEDIUM

    return {
        "susut_received_to_quarantine_pct": susut_received_to_quarantine_pct,
        "susut_lapangan_to_final_pct": susut_lapangan_to_final_pct,
        "yield_pct": yield_pct,
        "risk_level": risk_level.value,
        "flags_json": flags,
    }
