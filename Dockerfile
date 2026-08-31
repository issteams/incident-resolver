FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY dataset ./dataset
COPY baseline.py advanced.py evaluate.py ./

RUN pip install --no-cache-dir -e .

# LLM_PROVIDER, LLM_MODEL, OPENROUTER_API_KEY / OPENAI_API_KEY are passed
# at `docker run` time, e.g.:
#   docker run -e OPENROUTER_API_KEY=... -e LLM_MODEL=... incident-resolver evaluate.py
ENTRYPOINT ["python"]
CMD ["evaluate.py"]
