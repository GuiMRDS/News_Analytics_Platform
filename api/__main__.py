"""Sobe o servidor:  uv run python -m api  [--host 127.0.0.1] [--port 8000] [--reload]"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="News Analytics Platform · Quantum Terminal")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="recarrega ao editar arquivos (desenvolvimento)")
    args = parser.parse_args()
    print(f"\n  Quantum Terminal em http://{args.host}:{args.port}\n")
    uvicorn.run("api.servidor:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
