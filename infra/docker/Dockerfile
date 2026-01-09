FROM python:3.12-slim

# Install system dependencies for Rust and build
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Optimization: Copy only rust_core first to cache the heavy compilation step
# This prevents re-building Rust when unrelated root files change
COPY rust_core ./rust_core
COPY rust_core/pyproject.toml ./rust_core/

# Install maturin and build Rust extension
RUN pip install maturin
WORKDIR /app/rust_core
RUN maturin build --release

# Now copy the rest of the application
WORKDIR /app
COPY . .

# Install the pre-built Rust wheel
RUN pip install rust_core/target/wheels/*.whl

# Install Python dependencies including uvicorn for ASGI server
RUN pip install --no-cache-dir uvicorn[standard]
RUN pip install --no-cache-dir .

EXPOSE 20020
CMD ["python", "-m", "uvicorn", "somabrain.asgi:application", "--host", "0.0.0.0", "--port", "20020"]
