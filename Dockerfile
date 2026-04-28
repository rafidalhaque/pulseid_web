FROM python:3.14-slim
WORKDIR /app

COPY pyproject.toml uv.lock /app/
RUN apt-get update -y && apt-get install curl ca-certificates libpq-dev gcc -y && rm -rf /var/lib/apt/lists/*
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

RUN uv sync --frozen --no-dev
COPY . .
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
EXPOSE 5000
CMD ["/entrypoint.sh"]