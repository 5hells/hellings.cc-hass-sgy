FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*
ENV PIP_DISABLE_ROOT_WARNING=1
RUN python -m pip install --upgrade pip

VOLUME /app
WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

ENV NO_COLOR=yes_please
ENV LANG=C
CMD ["python", "-m", "pytest"]