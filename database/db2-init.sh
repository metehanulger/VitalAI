#!/bin/bash
su - "${DB2INSTANCE:-db2inst1}" -c "db2 connect to ${DBNAME} && db2 -tvf /opt/triaj/init.sql; db2 terminate"
