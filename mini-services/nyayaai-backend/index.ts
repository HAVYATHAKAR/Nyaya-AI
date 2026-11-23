/**
 * NyayaAI Backend mini-service launcher.
 *
 * Spawns the Python FastAPI server (uvicorn) on port 8000 with detached=true
 * so the Python process is reparented to init (PID 1) and survives the bash
 * session ending. Caddy proxies requests via `?XTransformPort=8000` to this port.
 */

import { spawn } from "node:child_process";
import { mkdirSync, appendFileSync, openSync, closeSync } from "node:fs";
import { resolve } from "node:path";

const BACKEND_DIR = "/home/z/my-project/backend";
const VENV_PYTHON = resolve(BACKEND_DIR, "venv/bin/python");
const LOG_FILE = resolve(BACKEND_DIR, "server.log");

mkdirSync(BACKEND_DIR, { recursive: true });

function log(msg: string) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  appendFileSync(LOG_FILE, line);
  console.log(line.trimEnd());
}

log("=== NyayaAI backend launcher starting (detached mode) ===");

const args = [
  "-m", "uvicorn",
  "app.main:app",
  "--host", "0.0.0.0",
  "--port", "8000",
  "--workers", "1",
];

log(`Spawning detached: ${VENV_PYTHON} ${args.join(" ")}`);

// Open log files for stdout/stderr — Python will write here directly
const outFd = openSync(LOG_FILE, "a");
const errFd = openSync(LOG_FILE, "a");

const proc = spawn(VENV_PYTHON, args, {
  cwd: BACKEND_DIR,
  env: {
    ...process.env,
    DATABASE_URL: "sqlite:///./data/db/nyayaai.db",
    PYTHONUNBUFFERED: "1",
  },
  detached: true,           // <-- key: reparent to init when this process exits
  stdio: ["ignore", outFd, errFd],  // <-- direct file descriptors, no pipes
});

proc.unref();  // <-- key: allow this bun process to exit independently

log(`Backend spawned detached. uvicorn PID: ${proc.pid}`);
log("Parent bun process will exit immediately. Python is reparented to init.");

// Exit immediately — Python keeps running as child of init
process.exit(0);
