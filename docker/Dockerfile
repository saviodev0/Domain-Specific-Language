FROM python:3.10-slim

WORKDIR /app

# ANTLR precisa do Java para gerar o lexer, que não é versionado.
RUN apt-get update \
	&& apt-get install -y --no-install-recommends default-jre-headless \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-antlr.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -r requirements-antlr.txt
COPY . /app
RUN sh gerar.sh

CMD ["python", "-u", "main.py"]