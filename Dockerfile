FROM sourcepole/qwc-uwsgi-base:alpine-latest

# Required for psychopg, --> https://github.com/psycopg/psycopg2/issues/684
RUN apk add --no-cache --update postgresql-dev gcc python3-dev musl-dev

ADD . /srv/qwc_service
RUN pip3 install --no-cache-dir -r /srv/qwc_service/requirements.txt

ENV SERVICE_MOUNTPOINT=/api/v1/print