FROM ghcr.io/astral-sh/uv:trixie-slim

# Install build tools as root during build
USER root
RUN apt-get update \
    && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create vscode user
RUN useradd -m -s /bin/bash vscode \
    && echo "vscode ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers


# Ensure workspace exists and is owned by vscode
RUN mkdir -p /workspace && chown -R vscode:vscode /workspace

# Switch to vscode for all runtime operations
USER vscode
WORKDIR /workspace/HA-Battery-Notes