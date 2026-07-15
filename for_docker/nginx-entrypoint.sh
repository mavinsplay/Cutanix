#!/bin/sh
set -e

mkdir -p /etc/nginx/user_conf.d
envsubst '$CUTANIX_DOMAIN' \
  < /etc/nginx/conf-template/cutanix_prod.conf.template \
  > /etc/nginx/user_conf.d/cutanix.conf

exec /docker-entrypoint.sh /scripts/start_nginx_certbot.sh
