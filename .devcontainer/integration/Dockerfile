FROM ghcr.io/astral-sh/uv:trixie-slim

# Create vscode user
RUN useradd -m -s /bin/bash vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers


# Ensure workspace exists and is owned by vscode
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

# Switch to vscode for all runtime operations
USER vscode
WORKDIR /workspace/HA-Battery-Notes