#!/bin/bash

set -u

instance="${DB2INSTANCE:-db2inst1}"
database="${DBNAME:?DBNAME must be set}"

if [[ ! "$database" =~ ^[[:alnum:]_]+$ ]]; then
  echo "DBNAME must contain only letters, digits, and underscores." >&2
  exit 1
fi

su - "$instance" -c "db2 connect to $database >/dev/null && db2 -tvf /opt/triaj/init.sql; result=\$?; db2 terminate >/dev/null 2>&1; exit \$result"
