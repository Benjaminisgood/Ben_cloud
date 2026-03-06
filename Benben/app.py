#!/usr/bin/env python3
from __future__ import annotations

try:
    from apps.main import app, settings
except ModuleNotFoundError:  # backward compatibility for legacy package layout
    from benben_api.main import app, settings  # type: ignore[no-redef]

__all__ = ["app", "settings"]

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
