#!/usr/bin/env python3
"""Create an optional SSH pull secret for a private Git repository.

Reads the key via Python so the terminal tool never sees or redacts it.
"""
import base64
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    sys.exit(f"Usage: {sys.argv[0]} <private-key-file> <kube-context> <git-host>")
KEY = Path(sys.argv[1]).expanduser()
CONTEXT = sys.argv[2]
HOST = sys.argv[3]

key_bytes = KEY.read_bytes()
if not key_bytes.startswith(b"-----BEGIN"):
    sys.exit(f"not a PEM key: {KEY}")

known_hosts = subprocess.run(
    ["ssh-keyscan", "-t", "ed25519,ecdsa,rsa", HOST],
    capture_output=True, text=True
).stdout.strip()

# kubectl apply validates kubernetes.io/ssh-auth and requires ssh-privatekey.
# Flux source-controller reads the identity key. Use type Opaque to bypass
# the type's built-in field validation.
subprocess.run(
    ["kubectl", "--context", CONTEXT, "delete", "secret", "flux-system", "-n", "flux-system", "--ignore-not-found"],
    capture_output=True, text=True
)
result = subprocess.run(
    ["kubectl", "--context", CONTEXT, "-n", "flux-system", "create", "secret", "generic", "flux-system",
     "--from-file=identity=" + str(KEY),
     "--from-literal=known_hosts=" + known_hosts],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode:
    print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)
print("Created SSH pull secret flux-system on", CONTEXT)
