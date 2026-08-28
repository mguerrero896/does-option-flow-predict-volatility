# Public methodological smoke container (decision 63).
# It runs only the synthetic demo: .dockerignore deliberately excludes the public
# evidence/docs tree as well as all licensed-derived data. The full hermetic suite
# belongs in GitHub Actions or a clean clone, where its tracked artifacts are present.
#
#   docker build -t mds650-repro .
#   docker run --rm mds650-repro                          # synthetic smoke demo
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY . .
RUN uv sync --locked

CMD ["uv", "run", "python", "scripts/run_public_repro_demo.py"]
