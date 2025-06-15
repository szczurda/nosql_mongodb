#!/bin/bash

# Helper: wait for Mongo to be ready on given container
wait_for_mongo() {
  local container=$1
  echo "Waiting for $container MongoDB to be ready..."
  until docker compose exec "$container" mongosh --eval "db.runCommand({ ping: 1 })" > /dev/null 2>&1; do
    echo "$container MongoDB not ready yet, waiting 5s..."
    sleep 5
  done
}

# === Step 1: Start all containers ===
echo "Starting containers..."
docker compose up -d || { echo "Failed to start containers"; exit 1; }

# === Step 2: Wait for and initialize replica sets ===
wait_for_mongo configsvr01
echo "Initializing config server replica set..."
docker compose exec configsvr01 bash scripts/init-configserver.js

wait_for_mongo shard01-a
echo "Initializing shard01..."
docker compose exec shard01-a bash scripts/init-shard01.js

wait_for_mongo shard02-a
echo "Initializing shard02..."
docker compose exec shard02-a bash scripts/init-shard02.js

wait_for_mongo shard03-a
echo "Initializing shard03..."
docker compose exec shard03-a bash scripts/init-shard03.js

# === Step 3: Wait until router is ready ===
wait_for_mongo router01
echo "Initializing router..."
docker compose exec router01 mongosh --host localhost:27017 -f scripts/init-router.js

# === Step 4: Setup authentication ===
echo "Setting up authentication..."
docker compose exec configsvr01 bash scripts/auth.js
docker compose exec shard01-a bash scripts/auth.js
docker compose exec shard02-a bash scripts/auth.js
docker compose exec shard03-a bash scripts/auth.js

# === Step 5: Enable sharding and setup shard key ===
echo "Enabling sharding on router..."

echo "Waiting for router to be ready for authenticated connections..."
until docker compose exec router01 mongosh -u "admin" -p "nosql_2025" --authenticationDatabase admin --eval "db.runCommand({ ping: 1 })" > /dev/null 2>&1; do
  echo "router01 not ready yet (auth), waiting another 5s..."
  sleep 5
done

docker compose exec router01 mongosh -u "admin" -p "nosql_2025" --authenticationDatabase admin -f scripts/enable-sharding.js

echo "MongoDB cluster initialized successfully."

echo "Waiting a bit before starting importer..."
sleep 5

docker compose --profile importer run importer

echo "Connecting to MongoDB shell on router01..."
docker compose exec router01 mongosh -u "admin" -p "nosql_2025" --authenticationDatabase admin