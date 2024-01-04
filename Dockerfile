FROM alpine:3.14

RUN apk add --no-cache dos2unix python3 py3-pip nginx bash

# build  + install python mysqlclient
RUN apk add --no-cache mariadb-connector-c-dev \
    && apk add --no-cache --virtual .build-deps \
        python3-dev build-base mariadb-dev \
    && pip install mysqlclient \
    && apk del .build-deps 

WORKDIR /pasta

RUN mkdir api
RUN mkdir /logs

COPY ./api/api.py ./api/
COPY ./api/clean_db.py ./api/
COPY ./api/server_db.py ./api/
COPY ./api/wsgi.py ./api/
COPY ./api/requirements.txt ./api/
COPY ./api/words.txt ./api/
COPY ./api/auth.json.secret.noauth ./api/auth.json.secret

COPY ./website ./website

COPY ./docker-nginx.conf /etc/nginx/nginx.conf
COPY ./docker-entrypoint.sh .

RUN dos2unix docker-entrypoint.sh

WORKDIR /pasta/api

RUN pip3 install -r requirements.txt

EXPOSE 80

ENTRYPOINT ["/pasta/docker-entrypoint.sh"]