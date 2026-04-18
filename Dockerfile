# Container image for the opsboard test suite (AfterQuery submission).
#
# Builds on a pinned slim Python base, installs a pinned uv, syncs the
# locked dependencies, and runs the test suite by default.

FROM python:3.12.8-slim

WORKDIR /app

# Install a pinned uv. pip ships with the base image, so uv is installed
# directly from PyPI rather than via a network bootstrap script.
RUN pip install --no-cache-dir uv==0.7.21

# Copy the full repository (including uv.lock and the .git directory, which
# AfterQuery relies on) into the build context.
COPY . .

# Install the locked dependencies, including the dev group used by pytest.
RUN uv sync --frozen

# Run the test suite by default.
CMD ["uv", "run", "pytest"]
