"""CLI command for launching the Strands Evals Web UI."""

import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def get_frontend_path() -> Path:
    """Get the path to the frontend directory."""
    return Path(__file__).parent / "frontend" / "strands-evals-ui"


def get_api_module() -> str:
    """Get the API module path for uvicorn."""
    return "strands_evals.web.api.main:app"


def start_backend(host: str = "127.0.0.1", port: int = 8000) -> subprocess.Popen:
    """Start the FastAPI backend server."""
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        get_api_module(),
        "--host",
        host,
        "--port",
        str(port),
    ]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def start_frontend(
    host: str = "127.0.0.1", port: int = 3000, api_url: str = "http://127.0.0.1:8000"
) -> subprocess.Popen:
    """Start the frontend development server (Next.js)."""
    frontend_path = get_frontend_path()

    if not frontend_path.exists():
        raise FileNotFoundError(f"Frontend directory not found: {frontend_path}")

    env = os.environ.copy()
    env["NEXT_PUBLIC_API_URL"] = api_url

    cmd = ["npm", "run", "dev", "--", "-H", host, "-p", str(port)]

    return subprocess.Popen(
        cmd,
        cwd=str(frontend_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for a server to become available."""
    import urllib.error
    import urllib.request

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, ConnectionRefusedError):
            time.sleep(0.5)
    return False


def main():
    """Main entry point for the strands web command."""
    parser = argparse.ArgumentParser(
        description="Launch the Strands Evals Web UI",
        prog="strands web",
    )
    parser.add_argument(
        "--backend-host",
        default="127.0.0.1",
        help="Host for the backend server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=8000,
        help="Port for the backend server (default: 8000)",
    )
    parser.add_argument(
        "--frontend-host",
        default="127.0.0.1",
        help="Host for the frontend server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Port for the frontend server (default: 3000)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open the browser automatically",
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Only start the backend server",
    )

    args = parser.parse_args()

    backend_url = f"http://{args.backend_host}:{args.backend_port}"
    frontend_url = f"http://{args.frontend_host}:{args.frontend_port}"

    processes = []

    def cleanup(signum=None, frame=None):
        """Clean up child processes."""
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        print("Starting Strands Evals Web UI...")
        print(f"Backend: {backend_url}")

        backend_proc = start_backend(args.backend_host, args.backend_port)
        processes.append(backend_proc)

        print("Waiting for backend to start...")
        if not wait_for_server(f"{backend_url}/api/health"):
            print("Error: Backend failed to start")
            cleanup()
            return

        print("Backend started successfully!")

        if not args.backend_only:
            print(f"Frontend: {frontend_url}")

            try:
                frontend_proc = start_frontend(
                    args.frontend_host,
                    args.frontend_port,
                    backend_url,
                )
                processes.append(frontend_proc)

                print("Waiting for frontend to start...")
                time.sleep(3)

                if not args.no_browser:
                    print(f"Opening browser at {frontend_url}")
                    webbrowser.open(frontend_url)

            except FileNotFoundError as e:
                print(f"Warning: {e}")
                print("Frontend not available. Running backend only.")
                print(f"You can access the API at {backend_url}")
                print(f"API documentation available at {backend_url}/docs")

        print("\nPress Ctrl+C to stop the servers")

        while True:
            for proc in processes:
                if proc.poll() is not None:
                    line = proc.stdout.readline() if proc.stdout else ""
                    if line:
                        print(line, end="")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup()


if __name__ == "__main__":
    main()
