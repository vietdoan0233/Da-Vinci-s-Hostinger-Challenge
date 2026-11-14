FROM python:3.12-slim
WORKDIR /code
COPY requirements-serve.txt .
RUN pip install --no-cache-dir --upgrade -r requirements-serve.txt
COPY ./app /code/app
CMD ["fastapi", "run", "app/main.py", "--proxy-headers", "--port", "8000"]
