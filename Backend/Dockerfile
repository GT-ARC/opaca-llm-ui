FROM python:3.10-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src Backend

COPY agents_tools.json .

EXPOSE 3001

ENTRYPOINT [ "python3", "-m", "Backend.server" ]
