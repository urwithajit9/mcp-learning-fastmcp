# devops_server.py
import subprocess
import platform
import psutil  # pip install psutil
import httpx
from datetime import datetime
from typing import Dict, List
from fastmcp import FastMCP

mcp = FastMCP("DevOpsMonitor 🖥️")


@mcp.tool
def get_system_health() -> Dict:
    """
    Get real-time system health metrics: CPU usage, memory, disk space, and uptime.
    Use this when the user asks about server health, system performance, or resource usage.
    Returns percentages and absolute values for all key metrics.
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time

    # Disk info for all partitions
    partitions = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            partitions.append(
                {
                    "mountpoint": partition.mountpoint,
                    "total_GB": round(usage.total / (1024**3), 1),
                    "used_GB": round(usage.used / (1024**3), 1),
                    "free_GB": round(usage.free / (1024**3), 1),
                    "percent_used": usage.percent,
                }
            )
        except PermissionError:
            continue

    return {
        "timestamp": datetime.now().isoformat(),
        "platform": platform.system(),
        "cpu": {
            "percent_used": cpu_percent,
            "core_count": psutil.cpu_count(),
            "status": "WARNING" if cpu_percent > 80 else "OK",
        },
        "memory": {
            "total_GB": round(memory.total / (1024**3), 1),
            "available_GB": round(memory.available / (1024**3), 1),
            "percent_used": memory.percent,
            "status": "WARNING" if memory.percent > 85 else "OK",
        },
        "disk": partitions,
        "uptime_hours": round(uptime.total_seconds() / 3600, 1),
    }


@mcp.tool
async def check_service_url(url: str, timeout_seconds: int = 5) -> Dict:
    """
    Check if a web service or API endpoint is reachable and measure response time.
    Use this when the user wants to know if a service is up, down, or slow.
    Returns HTTP status code, response time, and health assessment.

    Args:
        url: Full URL to check (e.g., 'https://api.myapp.com/health')
        timeout_seconds: Maximum wait time before marking as down (default: 5)
    """
    try:
        start = datetime.now()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout_seconds)
        elapsed_ms = (datetime.now() - start).total_seconds() * 1000

        return {
            "url": url,
            "status": "UP",
            "http_status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 1),
            "performance": (
                "FAST"
                if elapsed_ms < 200
                else "SLOW" if elapsed_ms < 1000 else "VERY SLOW"
            ),
        }
    except httpx.TimeoutException:
        return {"url": url, "status": "DOWN", "reason": "Connection timed out"}
    except Exception as e:
        return {"url": url, "status": "DOWN", "reason": str(e)}


@mcp.tool
def get_top_processes(limit: int = 5) -> Dict:
    """
    List the top resource-consuming processes on the system.
    Use this when the user asks what is using the most CPU or memory.
    Returns process name, PID, CPU%, and memory% for the heaviest processes.
    """
    processes = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = proc.info
            if info["cpu_percent"] is not None:
                processes.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort by CPU usage
    processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)

    return {
        "top_processes": [
            {
                "pid": p["pid"],
                "name": p["name"],
                "cpu_percent": round(p["cpu_percent"], 1),
                "memory_percent": round(p.get("memory_percent", 0), 1),
            }
            for p in processes[:limit]
        ],
        "limit": limit,
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8080, path="/mcp")
