FROM python:3.8-slim

# Install build tools and dependencies
RUN apt-get update && \
    apt-get install -y build-essential python3-dev

# Upgrade pip
RUN python -m pip install --upgrade pip

RUN pip3 install flask redis minio requests

WORKDIR /srv



COPY rest-server.py /srv
EXPOSE 5000
CMD ["python", "rest-server.py"]