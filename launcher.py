from __future__ import annotations

import ctypes
import os
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.request import urlopen


def _resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _data_path() -> Path:
    root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    target = root / "Hera" / "data"
    target.mkdir(parents=True, exist_ok=True)
    return target


def main() -> None:
    try:
        with urlopen("http://127.0.0.1:8000/api/health", timeout=1) as response:
            if response.status == 200:
                webbrowser.open("http://127.0.0.1:8000")
                return
    except Exception:
        pass

    os.environ.setdefault("HERA_DATA_DIR", str(_data_path()))

    import uvicorn
    from fastapi.staticfiles import StaticFiles
    from backend.app.main import app

    frontend = _resource_path("frontend")
    if not frontend.joinpath("index.html").exists():
        raise RuntimeError("Os arquivos da interface não foram encontrados.")

    app.mount("/", StaticFiles(directory=frontend, html=True), name="frontend")
    if os.getenv("HERA_NO_BROWSER", "0") != "1":
        threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    # Executáveis com --windowed não possuem stdout/stderr. Desabilitar a
    # configuração padrão de logs evita que o Uvicorn tente criar formatadores
    # de terminal e encerre o aplicativo durante a inicialização.
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Não foi possível iniciar o Hera.\n\n{exc}",
            "Hera",
            0x10,
        )
        raise
