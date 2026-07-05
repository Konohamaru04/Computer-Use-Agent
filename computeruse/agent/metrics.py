from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

from computeruse.config import DEBUG_TIMING_LOG_PATH, ensure_runtime_dirs


class GpuMetric(TypedDict):
    name: str
    util_percent: float | None
    memory_used_mb: float | None
    memory_total_mb: float | None


@dataclass
class MetricsSampler:
    process: Any | None = None

    def __post_init__(self) -> None:
        try:
            import psutil

            self.process = psutil.Process()
            self.process.cpu_percent(interval=None)
            psutil.cpu_percent(interval=None)
        except Exception:
            self.process = None

    def sample(self) -> dict[str, Any]:
        started = time.perf_counter()
        metrics: dict[str, Any] = {}
        metrics.update(_sample_psutil(self.process))
        metrics.update(_sample_gpu())
        metrics["metrics_ms"] = int((time.perf_counter() - started) * 1000)
        return metrics


def append_debug_timing_log(record: dict[str, Any], path: Path = DEBUG_TIMING_LOG_PATH) -> None:
    ensure_runtime_dirs()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, separators=(",", ":"), default=str) + "\n")


def _sample_psutil(process: Any | None) -> dict[str, Any]:
    try:
        import psutil
    except Exception as exc:
        return {"metrics_available": False, "metrics_error": f"psutil unavailable: {exc}"}

    metrics: dict[str, Any] = {"metrics_available": True}
    try:
        cpu_times = psutil.cpu_times_percent(interval=None)
        metrics["cpu_percent"] = _round(psutil.cpu_percent(interval=None))
        metrics["cpu_user_percent"] = _round(getattr(cpu_times, "user", 0.0))
        metrics["cpu_system_percent"] = _round(getattr(cpu_times, "system", 0.0))
    except Exception as exc:
        metrics["cpu_error"] = str(exc)

    try:
        memory = psutil.virtual_memory()
        metrics["ram_percent"] = _round(memory.percent)
        metrics["ram_used_mb"] = _bytes_to_mb(memory.used)
        metrics["ram_available_mb"] = _bytes_to_mb(memory.available)
        metrics["ram_total_mb"] = _bytes_to_mb(memory.total)
    except Exception as exc:
        metrics["ram_error"] = str(exc)

    if process is not None:
        try:
            metrics["process_cpu_percent"] = _round(process.cpu_percent(interval=None))
            process_memory = process.memory_info()
            metrics["process_rss_mb"] = _bytes_to_mb(process_memory.rss)
            metrics["process_vms_mb"] = _bytes_to_mb(process_memory.vms)
            metrics["process_threads"] = process.num_threads()
        except Exception as exc:
            metrics["process_error"] = str(exc)

    try:
        disk = psutil.disk_io_counters()
        if disk:
            metrics["disk_read_mb"] = _bytes_to_mb(disk.read_bytes)
            metrics["disk_write_mb"] = _bytes_to_mb(disk.write_bytes)
    except Exception as exc:
        metrics["disk_error"] = str(exc)

    return metrics


def _sample_gpu() -> dict[str, Any]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {"gpu_available": False, "gpu_source": "nvidia-smi not found"}

    try:
        completed = subprocess.run(
            [
                nvidia_smi,
                "--query-gpu=name,utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except Exception as exc:
        return {"gpu_available": False, "gpu_source": "nvidia-smi", "gpu_error": str(exc)}

    gpus: list[GpuMetric] = []
    for line in completed.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            continue
        name, util, mem_used, mem_total = parts[:4]
        gpus.append(
            {
                "name": name,
                "util_percent": _safe_float(util),
                "memory_used_mb": _safe_float(mem_used),
                "memory_total_mb": _safe_float(mem_total),
            }
        )

    if not gpus:
        return {"gpu_available": False, "gpu_source": "nvidia-smi", "gpu_error": "no GPU rows returned"}

    total_memory = sum((gpu["memory_total_mb"] or 0.0) for gpu in gpus)
    used_memory = sum((gpu["memory_used_mb"] or 0.0) for gpu in gpus)
    avg_util = sum((gpu["util_percent"] or 0.0) for gpu in gpus) / len(gpus)
    return {
        "gpu_available": True,
        "gpu_source": "nvidia-smi",
        "gpu_count": len(gpus),
        "gpu_names": ", ".join(gpu["name"] for gpu in gpus),
        "gpu_util_percent": _round(avg_util),
        "gpu_memory_used_mb": _round(used_memory),
        "gpu_memory_total_mb": _round(total_memory),
        "gpus": gpus,
    }


def _bytes_to_mb(value: int | float) -> float:
    return _round(float(value) / (1024 * 1024))


def _round(value: int | float) -> float:
    return round(float(value), 1)


def _safe_float(value: str) -> float | None:
    try:
        return _round(float(value))
    except ValueError:
        return None
