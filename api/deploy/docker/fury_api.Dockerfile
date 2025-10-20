###############################################
# Base Image
###############################################
ARG PYTHON_VERSION=3.12.4

FROM python:${PYTHON_VERSION}-slim AS python-base

ARG POETRY_VERSION=1.8.3

# Set work directory
ENV APP_PATH="/app"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=off \
  PIP_DISABLE_PIP_VERSION_CHECK=on \
  PIP_DEFAULT_TIMEOUT=100 \
  POETRY_VERSION=${POETRY_VERSION} \
  POETRY_VIRTUALENVS_IN_PROJECT=true \
  POETRY_NO_INTERACTION=1 \
  PYSETUP_PATH="/opt/pysetup" \
  VENV_PATH="/opt/pysetup/.venv" \
  POETRY_HOME="/opt/poetry"

# Prepend venv to path
ENV PATH="${VENV_PATH}/bin:${POETRY_HOME}/bin:${PATH}"

# Add python modules to path
ENV PYTHONPATH="${APP_PATH}/src:${APP_PATH}:${PYTHONPATH:-}"

###############################################
# Builder Image
###############################################
FROM python-base AS builder-base

# Install necessary build tools and networking tools for debugging (curl, ping, posgres client)
RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  build-essential \
  make \
  curl \
  iputils-ping \
  postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# Copy files to keep cached in this stage
WORKDIR ${PYSETUP_PATH}
COPY Makefile poetry.lock pyproject.toml ./

# Install poetry and dependencies
RUN pip install poetry==${POETRY_VERSION} \
  && make prod-install \
  && pip install pydevd-pycharm~=222.4167.33 \
  && rm -rf /root/.cache

###############################################
# Production Image
###############################################
FROM python-base AS production

# Install necessary networking tools in the production image too (I should not need make, curl, ping or posgresql client in the production image)
RUN apt-get update \
  && apt-get install --no-install-recommends -y \
  libgl1 \
  libglib2.0-0 \
  make \
  curl \
  iputils-ping \
  postgresql-client \
  && rm -rf /var/lib/apt/lists/*

# Copy dependencies from builder
COPY --from=builder-base ${PYSETUP_PATH} ${PYSETUP_PATH}

# Copy application code
COPY . ${APP_PATH}

# Create and set up the application user
RUN useradd -m -d "${APP_PATH}" -s /bin/bash app \
  && chown -R app:app "${APP_PATH}/"

WORKDIR ${APP_PATH}
USER app

EXPOSE 3000

# Run the application
CMD ["python", "-m", "fury_api"]
