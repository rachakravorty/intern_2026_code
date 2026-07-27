import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any

class TestStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

@dataclass
class TestResult:
    """Encapsulates test status, runtime, and hardware telemetry for GUI display."""
    suite_name: str
    test_id: str
    description: str
    status: TestStatus = TestStatus.PENDING
    duration_s: float = 0.0
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite": self.suite_name,
            "test_id": self.test_id,
            "description": self.description,
            "status": self.status.value,
            "duration_s": round(self.duration_s, 3),
            "message": self.message,
            "metrics": self.metrics,
        }