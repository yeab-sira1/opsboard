# Test runner image for the OpsBoard test suite.

FROM python:3.12-slim

LABEL org.opencontainers.image.description="OpsBoard test suite"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install a pinned uv.
RUN pip install --no-cache-dir uv==0.7.21

# Copy dependency manifests first so that the layer is cached independently
# from source changes.
COPY pyproject.toml uv.lock ./

# Install locked dependencies without installing the project itself.
RUN uv sync --frozen --no-install-project

# Copy the full source tree (including the project package).
COPY . .

# Install the project itself now that its source is present.
RUN uv sync --frozen

CMD ["uv", "run", "pytest"]
