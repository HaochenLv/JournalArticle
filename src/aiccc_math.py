"""Pure AICCC SLA-to-network accounting kernel.

This module contains no request scheduler or execution simulator. It implements
only the mathematical accounting used by the AICCC evaluator:

    SLA budget - profiled compute - accounting-only charges
      -> residual network time
      -> per-link time budgets
      -> per-link bandwidth commitments.

The path allocation follows Eqs. (22)--(24) of the AICCC manuscript.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

EPS = 1e-9


class AccountingError(ValueError):
    """Base class for invalid AICCC accounting inputs."""


class ResidualBudgetExhausted(AccountingError):
    """Raised when no positive time remains for network service."""


class NonPositiveLinkCapacity(AccountingError):
    """Raised when positive traffic is assigned to a non-positive link."""


@dataclass(frozen=True)
class ResidualBudget:
    limit_s: float
    compute_s: float
    intrinsic_s: float = 0.0
    blocking_s: float = 0.0
    fixed_s: float = 0.0
    queue_s: float = 0.0

    @property
    def accounted_s(self) -> float:
        return (
            self.compute_s
            + self.intrinsic_s
            + self.blocking_s
            + self.fixed_s
            + self.queue_s
        )

    @property
    def network_s(self) -> float:
        return self.limit_s - self.accounted_s


@dataclass(frozen=True)
class LinkCommitment:
    link_id: str
    bytes: float
    capacity_bytes_per_s: float
    ideal_serialization_s: float
    weight: float
    allocated_time_s: float
    required_bandwidth_bytes_per_s: float

    @property
    def relative_capacity(self) -> float:
        return self.required_bandwidth_bytes_per_s / self.capacity_bytes_per_s


def residual_network_budget(
    limit_s: float,
    compute_s: float,
    *,
    intrinsic_s: float = 0.0,
    blocking_s: float = 0.0,
    fixed_s: float = 0.0,
    queue_s: float = 0.0,
) -> ResidualBudget:
    """Return the AICCC residual network-time budget.

    All arguments are accounting quantities. This function never modifies
    request progress or event timing.
    """
    values = {
        "limit_s": limit_s,
        "compute_s": compute_s,
        "intrinsic_s": intrinsic_s,
        "blocking_s": blocking_s,
        "fixed_s": fixed_s,
        "queue_s": queue_s,
    }
    if any(not math.isfinite(v) for v in values.values()):
        raise AccountingError(f"non-finite accounting input: {values}")
    if limit_s < 0 or any(
        values[k] < 0
        for k in ("compute_s", "intrinsic_s", "blocking_s", "fixed_s", "queue_s")
    ):
        raise AccountingError(f"negative accounting input: {values}")
    return ResidualBudget(**values)


def path_commitments(
    demand_bytes: dict[str, float],
    capacities_bytes_per_s: dict[str, float],
    residual_s: float,
    *,
    eps: float = EPS,
) -> dict[str, LinkCommitment]:
    """Allocate residual network time and derive required link bandwidth.

    For active link e:
        omega_e = (S_e / B_e) / sum_j(S_j / B_j)
        delta_e = omega_e * residual_s
        b_req_e = S_e / delta_e

    The returned allocations therefore sum to residual_s (up to roundoff), and
    each traversed link receives the same relative bandwidth utilization.
    """
    if not math.isfinite(residual_s):
        raise AccountingError("residual_s must be finite")
    if residual_s <= eps:
        raise ResidualBudgetExhausted(
            f"residual network budget must be > {eps}, got {residual_s}"
        )

    active: list[tuple[str, float, float]] = []
    for link_id, raw_bytes in demand_bytes.items():
        if not math.isfinite(raw_bytes) or raw_bytes < 0:
            raise AccountingError(f"invalid demand on {link_id}: {raw_bytes}")
        if raw_bytes == 0:
            continue
        if link_id not in capacities_bytes_per_s:
            raise AccountingError(f"missing capacity for {link_id}")
        capacity = capacities_bytes_per_s[link_id]
        if not math.isfinite(capacity) or capacity <= 0:
            raise NonPositiveLinkCapacity(
                f"positive traffic on {link_id} with capacity {capacity}"
            )
        active.append((link_id, raw_bytes, capacity))

    if not active:
        return {}

    ideal = {link_id: size / capacity for link_id, size, capacity in active}
    total_ideal = sum(ideal.values())
    if not math.isfinite(total_ideal) or total_ideal <= 0:
        raise AccountingError(f"invalid total ideal serialization time: {total_ideal}")

    out: dict[str, LinkCommitment] = {}
    for link_id, size, capacity in active:
        weight = ideal[link_id] / total_ideal
        allocated = weight * residual_s
        if allocated <= 0:
            raise AccountingError(f"non-positive allocated time on {link_id}")
        required = size / allocated
        out[link_id] = LinkCommitment(
            link_id=link_id,
            bytes=size,
            capacity_bytes_per_s=capacity,
            ideal_serialization_s=ideal[link_id],
            weight=weight,
            allocated_time_s=allocated,
            required_bandwidth_bytes_per_s=required,
        )
    return out


def aggregate_link_commitments(
    per_request: dict[str, dict[str, LinkCommitment]],
) -> dict[str, float]:
    """Aggregate request commitments on shared physical links."""
    totals: dict[str, float] = {}
    for commitments in per_request.values():
        for link_id, item in commitments.items():
            totals[link_id] = totals.get(link_id, 0.0) + item.required_bandwidth_bytes_per_s
    return totals
