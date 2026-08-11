
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    MAX_STEPS = "max_steps_exceeded"


@dataclass
class Task:
    task_id: str
    question: str
    csv_path: str
    expected_answer: Optional[str] = None
    tolerance: float = 0.02


@dataclass
class Step:
    index: int
    timestamp: float
    kind: str
    content: Any
    ok: Optional[bool] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trajectory:
    task: Task
    steps: list = field(default_factory=list)
    status: Status = Status.RUNNING
    final_answer: Optional[str] = None
    consecutive_failures: int = 0

    def record(self, kind: str, content: Any, ok: Optional[bool] = None) -> Step:
        step = Step(index=len(self.steps), timestamp=time.time(), kind=kind, content=content, ok=ok)
        self.steps.append(step)
        return step

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            for step in self.steps:
                f.write(json.dumps(step.to_dict(), default=str) + "\n")

    def summary(self) -> str:
        lines = [f"Task: {self.task.question}", f"Status: {self.status.value}", f"Steps: {len(self.steps)}"]
        if self.final_answer is not None:
            lines.append(f"Final answer: {self.final_answer}")
        return "\n".join(lines)