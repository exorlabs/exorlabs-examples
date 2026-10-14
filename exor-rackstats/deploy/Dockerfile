FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY server/ /app/
USER 10001:10001
CMD ["python", "-m", "rackstats_agent"]
