FROM python:3.12.4-slim

ARG DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}

# Какие зависимости ставить: dev.txt (с debug-toolbar) или prod.txt (только base)
ARG REQUIREMENTS=dev.txt

RUN apt-get update --allow-releaseinfo-change -y \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      gnupg \
      dirmngr \
      git \
      gettext \
      build-essential \
      libpq-dev \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

COPY ./requirements /requirements
RUN pip install --upgrade pip \
 && pip install -r /requirements/${REQUIREMENTS}
RUN rm -rf /requirements

COPY ./cutanix /cutanix/
COPY ./manage.py /manage.py
COPY ./users /users/
COPY ./analysis /analysis/
COPY ./payments /payments/
COPY ./api /api/
COPY ./webapp /webapp/
COPY ./bot /bot/
COPY ./templates /templates/
COPY ./static_dev /static_dev/

WORKDIR /

RUN mkdir -p /logs /static /media

CMD python manage.py migrate \
 && python manage.py init_superuser \
 && python manage.py collectstatic --no-input \
 && gunicorn cutanix.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120
