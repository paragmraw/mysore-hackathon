FROM python:3.12-slim AS deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim AS runner
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    DATA_DIR=/app/data

RUN addgroup --system --gid 1001 appgroup \
    && adduser --system --uid 1001 appuser

COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin/gunicorn /usr/local/bin/gunicorn
COPY --chown=appuser:appgroup . .

RUN chown appuser:appgroup /app && mkdir -p /app/db && chown appuser:appgroup /app/db


RUN DJANGO_SECRET_KEY=build-only-collectstatic python manage.py collectstatic --noinput

RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

USER appuser
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "-b", "0.0.0.0:8000", "config.wsgi:application", "--workers", "2"]
