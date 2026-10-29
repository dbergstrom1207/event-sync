FROM python:3.12-slim
WORKDIR /app
COPY . .
USER 65534:65534
EXPOSE 8000
CMD ["python", "app.py", "--host", "0.0.0.0"]
