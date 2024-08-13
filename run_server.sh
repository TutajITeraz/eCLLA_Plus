#!/bin/bash

export DUBO_API_KEY="pk.bb63cda35d47463fb858192bee22510f"

while true; do
  echo "server run:" >> run_server.log
  date >> run_server.log

  python manage.py runserver 0.0.0.0:8080
done
