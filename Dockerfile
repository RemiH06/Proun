# Proun publicado: una sola imagen con la API, la landing (docs/) y el build
# del frontend, servidos por uvicorn desde el mismo origen (ver api/main.py).
# Versiones fijas. Pillow 13: la 10.4 tenía 69 CVE conocidos (pip-audit,
# 2026-11-14), y las 979 pruebas pasan igual con la 13.

FROM node:24.22.1-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13.17-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir Pillow==13.0.0 fastapi==0.142.2 uvicorn==0.30.6 \
    && useradd --create-home --uid 10001 proun
WORKDIR /app
COPY proun/ proun/
COPY api/ api/
COPY recolorear.py ./
COPY docs/ docs/
COPY --from=frontend /frontend/dist frontend/dist
# fuentes/ llega montada de solo lectura; wallpapers/ es un volumen que el
# usuario sin privilegios tiene que poder escribir.
RUN mkdir fuentes wallpapers && chown proun:proun wallpapers
USER proun
EXPOSE 8030
# 0.0.0.0 dentro del contenedor (su propia red); en el host se publica solo
# en 127.0.0.1, ver compose.yml.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8030", "--no-server-header"]
