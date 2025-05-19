FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src Backend

EXPOSE 3001

#ENTRYPOINT [ "python3", "-m", "Backend.server" ]
ENTRYPOINT [ "python3", "-u", "-m", "Backend.server" ]
