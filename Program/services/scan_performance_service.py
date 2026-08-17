"""
Trader_7_12 Pro

Scan Performance Service
Version 0.1

Purpose:
- measure scanner stages without requiring a live BCS connection;
- make the 20–30 second scan target explicit;
- provide a small, dependency-free timing utility for UI/logging/tests.

The service is deliberately read-only. It does not change scanner decisions,
market data, ranking, or order behavior.
"""

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class ScanStage:
    name: str
    started_at: float
    finished_at: float | None = None

    @property
    def elapsed_seconds(self) -> float:
        end = self.finished_at if self.finished_at is not None else monotonic()
        return max(0.0, end - self.started_at)


@dataclass
class ScanPerformanceReport:
    target_seconds: float = 30.0
    stages: list[ScanStage] = field(default_factory=list)
    started_at: float = field(default_factory=monotonic)
    finished_at: float | None = None

    @property
    def total_seconds(self) -> float:
        end = self.finished_at if self.finished_at is not None else monotonic()
        return max(0.0, end - self.started_at)

    @property
    def within_target(self) -> bool:
        return self.total_seconds <= self.target_seconds

    def stage(self, name: str) -> ScanStage:
        for item in self.stages:
            if item.name == name:
                return item
        raise KeyError(name)

    def summary(self) -> dict:
        return {
            "total_seconds": round(self.total_seconds, 3),
            "target_seconds": self.target_seconds,
            "within_target": self.within_target,
            "stages": {
                item.name: round(item.elapsed_seconds, 3)
                for item in self.stages
            },
        }


class ScanPerformanceService:
    """Tiny timing helper used by the scanner and offline regression tests."""

    TARGET_SECONDS = 30.0
    GOOD_SECONDS = 25.0

    def __init__(self, target_seconds: float | None = None):
        target = self.TARGET_SECONDS if target_seconds is None else float(target_seconds)
        if target <= 0:
            raise ValueError("target_seconds must be > 0")
        self.report = ScanPerformanceReport(target_seconds=target)
        self._active_stage: ScanStage | None = None

    def start_stage(self, name: str) -> ScanStage:
        if not name or not str(name).strip():
            raise ValueError("stage name must not be empty")
        if self._active_stage is not None:
            self.finish_stage()
        stage = ScanStage(name=str(name).strip(), started_at=monotonic())
        self.report.stages.append(stage)
        self._active_stage = stage
        return stage

    def finish_stage(self) -> ScanStage | None:
        stage = self._active_stage
        if stage is None:
            return None
        stage.finished_at = monotonic()
        self._active_stage = None
        return stage

    def finish(self) -> ScanPerformanceReport:
        self.finish_stage()
        if self.report.finished_at is None:
            self.report.finished_at = monotonic()
        return self.report

    def reset(self) -> None:
        self.report = ScanPerformanceReport(target_seconds=self.report.target_seconds)
        self._active_stage = None

    @staticmethod
    def classify(total_seconds: float, target_seconds: float = TARGET_SECONDS) -> str:
        value = float(total_seconds)
        target = float(target_seconds)
        if value <= target * 0.5:
            return "EXCELLENT"
        if value <= 25.0:
            return "GOOD"
        if value <= target:
            return "TARGET"
        return "SLOW"

    def formatted_status(self) -> str:
        report = self.finish()
        label = self.classify(report.total_seconds, report.target_seconds)
        return f"SCAN {report.total_seconds:.1f}s / target {report.target_seconds:.0f}s • {label}"
