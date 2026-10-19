#!/usr/bin/env bash
# Download PlantUML (once) and run its built-in web server, so the Zudoku build can render .puml files.
# Usage: plantuml-server.sh start|stop|status   (PLANTUML_PORT overrides the port, default 18080)
set -euo pipefail

VERSION=1.2026.9
SHA256=aa4a1d06f8911c4b842beff4828dd955be431692b631a312d04c0e9fab9581de
URL="https://github.com/plantuml/plantuml/releases/download/v${VERSION}/plantuml-${VERSION}.jar"
PORT="${PLANTUML_PORT:-18080}"
CACHE="$(cd "$(dirname "$0")/.." && pwd)/.cache"
JAR="$CACHE/plantuml-${VERSION}.jar"
PIDFILE="$CACHE/plantuml-server.pid"
LOG="$CACHE/plantuml-server.log"

# Ask for a minimal diagram, hex-encoded in the URL.
is_up() { curl -sf -o /dev/null "http://127.0.0.1:${PORT}/svg/~h$(printf '@startuml\nA -> B\n@enduml' | od -An -tx1 | tr -d ' \n')"; }

case "${1:-}" in
  start)
    command -v java >/dev/null || { echo "Java is required to run PlantUML." >&2; exit 1; }
    if is_up; then echo "PlantUML server already running on port ${PORT}."; exit 0; fi
    mkdir -p "$CACHE"
    if [ ! -f "$JAR" ]; then
      echo "Downloading PlantUML ${VERSION}..."
      curl -fL --silent --show-error -o "$JAR.part" "$URL"
      echo "${SHA256}  $JAR.part" | sha256sum -c --quiet - || { rm -f "$JAR.part"; echo "Checksum mismatch for the downloaded jar." >&2; exit 1; }
      mv "$JAR.part" "$JAR"
    fi
    nohup java -Djava.awt.headless=true -jar "$JAR" "-picoweb:${PORT}:127.0.0.1" >"$LOG" 2>&1 &
    echo $! >"$PIDFILE"
    for _ in $(seq 1 40); do
      if is_up; then echo "PlantUML server running on http://127.0.0.1:${PORT} (stop it with: $0 stop)."; exit 0; fi
      sleep 0.5
    done
    echo "PlantUML server did not start; see $LOG" >&2
    exit 1
    ;;
  stop)
    if [ -f "$PIDFILE" ] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
      while is_up; do sleep 0.2; done
      echo "PlantUML server stopped."
    else
      echo "PlantUML server was not running."
    fi
    rm -f "$PIDFILE"
    ;;
  status)
    if is_up; then echo "running on port ${PORT}"; else echo "not running"; exit 1; fi
    ;;
  *)
    echo "Usage: $0 start|stop|status" >&2
    exit 2
    ;;
esac
