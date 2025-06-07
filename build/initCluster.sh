#!/bin/bash

# === Step 1: Start all containers ===
echo "Starting containers..."
docker-compose up -d || { echo "Failed to start containers"; exit 1; }

# === Step 2: Initialize replica sets ===
echo "Initializing config server replica set..."
docker-compose exec configsvr01 bash "/scripts/init-configserver.js"

echo "Initializing shard01..."
docker-compose exec shard01-a bash "/scripts/init-shard01.js"

echo "Initializing shard02..."
docker-compose exec shard02-a bash "/scripts/init-shard02.js"

echo "Initializing shard03..."
docker-compose exec shard03-a bash "/scripts/init-shard03.js"

# === Step 3: Initialize the router ===
echo "Waiting 10 seconds for primary elections..."
sleep 10

echo "Initializing router..."
docker-compose exec router01 sh -c "mongosh < /scripts/init-router.js"

# === Step 4: Setup authentication ===
echo "Setting up authentication..."
docker-compose exec configsvr01 bash "/scripts/auth.js"
docker-compose exec shard01-a bash "/scripts/auth.js"
docker-compose exec shard02-a bash "/scripts/auth.js"
docker-compose exec shard03-a bash "/scripts/auth.js"

# === Step 5: Enable sharding and setup shard key ===
echo "Enabling sharding on router..."
docker-compose exec router01 mongosh --port 27017 -u "your_admin" --authenticationDatabase admin <<EOF
sh.enableSharding("MyDatabase")
db.adminCommand({ shardCollection: "MyDatabase.MyCollection", key: { oemNumber: "hashed", zipCode: 1, supplierId: 1 } })
EOF

echo "MongoDB cluster initialized successfully."
