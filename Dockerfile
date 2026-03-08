FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

# Zerochan requires a username in the User-Agent header.
# Pass this at runtime: docker run -e ZEROCHAN_USERNAME=YourUsername ...
ENV ZEROCHAN_USERNAME=""

CMD ["python", "server.py"]
