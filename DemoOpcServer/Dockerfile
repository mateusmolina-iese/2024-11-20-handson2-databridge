FROM python:3.11

WORKDIR /app

RUN pip install asyncua aiohttp

COPY . .

EXPOSE 8080

CMD ["python", "./OpcServer.py"]