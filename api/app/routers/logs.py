from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
async def get_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    level: str = Query(default="DEBUG", description="Minimum log level: DEBUG, INFO, WARNING, ERROR"),
):
    """Get recent log entries, newest first."""
    log_handler = request.app.state.log_handler

    level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
    min_priority = level_priority.get(level.upper(), 0)

    all_entries = list(log_handler.buffer)
    filtered = [
        e for e in all_entries
        if level_priority.get(e["level"], 0) >= min_priority
    ]

    # Newest first
    filtered.reverse()
    page = filtered[offset : offset + limit]

    return {
        "entries": page,
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
    }
