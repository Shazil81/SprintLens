FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
RUN useradd --create-home sprintlens && mkdir -p /var/lib/celery && chown -R sprintlens:sprintlens /app /var/lib/celery
USER sprintlens
CMD ["python", "-m", "gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]
