FROM python:3.12-slim
WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN apt-get update -y && apt-get install curl ca-certificates -y && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

RUN uv sync --frozen --no-dev
COPY . .
EXPOSE 5000
CMD ["uv", "run", "gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]