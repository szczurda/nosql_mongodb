#!/bin/bash

mongosh <<EOF
use admin;
db.createUser({user: "admin", pwd: "nosql_2025", roles:[{role: "root", db: "admin"}]});
exit;
EOF