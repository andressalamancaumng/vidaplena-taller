FROM python:3.11-slim AS base

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY init-db ./init-db

# El proceso HTTP no necesita permisos de root dentro del contenedor.
RUN useradd --create-home --uid 10001 vidaplena
USER vidaplena

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

# Esta etapa solo se construye para las pruebas; no engorda la imagen de la aplicación.
FROM base AS pruebas
USER root
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt
COPY tests ./tests
USER vidaplena
CMD ["python", "-m", "pytest", "-v", "-p", "no:cacheprovider", "tests"]

FROM base AS runtime
