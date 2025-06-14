from pymongo import MongoClient
from bson.min_key import MinKey
from bson.max_key import MaxKey
import time, os, json
from collections import defaultdict

# Config
DATA_PATH = "/python/data"
SHARD_COUNT = 3
MIN_PREFIX = 3
MAX_PREFIX = 7
MAX_CHUNK_SIZE = 10000  # max dokumentů na prefix (adaptivní dělení)

def ensure_data_dir(path):
    if not os.path.isdir(path) or not os.listdir(path):
        print(f"Data path '{path}' invalid or empty.")
        exit(1)
    print(f"Files in '{path}':", *os.listdir(path), sep="\n - ")

def connect_mongo(uri, retries=10, delay=5):
    for _ in range(retries):
        try:
            client = MongoClient(uri)
            client.admin.command("ping")
            print("Connected to MongoDB")
            return client
        except Exception as e:
            print(f"MongoDB not ready: {e}")
            time.sleep(delay)
    print("Connection to MongoDB failed")
    exit(1)

def import_json_files(db, path):
    for fname in os.listdir(path):
        if not fname.endswith('.json'):
            continue
        cname = fname[:-5]
        fpath = os.path.join(path, fname)
        print(f"Importing {fpath} into '{cname}'")
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                db[cname].insert_many(data)
                print(f"Inserted {len(data)} documents")
            elif isinstance(data, dict):
                db[cname].insert_one(data)
                print("Inserted 1 document")
            else:
                print(f"No valid data in {fname}")
        except Exception as e:
            print(f"Import failed for {fname}: {e}")

def get_prefix_counts(col, plen, base=None):
    match = {"geohash": {"$exists": True}}
    if base:
        match["geohash"]["$regex"] = f"^{base}"
    pipeline = [
        {"$match": match},
        {"$group": {"_id": {"$substrCP": ["$geohash", 0, plen]}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    return list(col.aggregate(pipeline))

def split_prefixes(col, prefixes, plen):
    result = []
    for p in prefixes:
        if p['count'] > MAX_CHUNK_SIZE and plen < MAX_PREFIX:
            children = get_prefix_counts(col, plen + 1, p['_id'])
            if children:
                result.extend(split_prefixes(col, children, plen + 1))
            else:
                result.append(p)
        else:
            result.append(p)
    return result

def adaptive_prefix_counts(col, min_p, max_p):
    return split_prefixes(col, get_prefix_counts(col, min_p), min_p)

def get_shards(admin):
    return [s['_id'] for s in admin.command("listShards")['shards']]

def retry_mongo_command(func, max_retries=5, delay=5):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            if "ConflictingOperationInProgress" in str(e):
                print(f"Retrying due to conflict... ({i+1}/{max_retries})")
                time.sleep(delay)
            else:
                raise e
    print("Max retries exceeded.")
    return None

def increment_string(s):
    # Inkrement posledního znaku řetězce (pro jemné posunutí hranic)
    if not s:
        return 'a'
    last_char = s[-1]
    if last_char == 'z':
        return increment_string(s[:-1]) + 'a'
    return s[:-1] + chr(ord(last_char) + 1)

def save_zone_tags(admin, ns, zone_ranges):
    config_db = admin.client['config']
    # Smažeme existující tagy pro daný namespace
    config_db.tags.delete_many({"ns": ns})

    for zone, min_g, max_g in zone_ranges:
        min_key = {"geohash": min_g}
        max_key_str = max_g + "z" * (12 - len(max_g))
        max_key = {"geohash": max_key_str}
        doc = {
            "ns": ns,
            "min": min_key,
            "max": max_key,
            "tag": zone
        }
        try:
            config_db.tags.insert_one(doc)
        except Exception as e:
            print(f"Failed to insert tag for {zone}: {e}")

def update_collection_tags(admin, ns, zone_ranges):
    config_db = admin.client['config']
    tags = []
    for zone, min_g, max_g in zone_ranges:
        min_key = {"geohash": min_g}
        max_key_str = max_g + "z" * (12 - len(max_g))
        max_key = {"geohash": max_key_str}
        tags.append({
            "tag": zone,
            "min": min_key,
            "max": max_key
        })
    try:
        config_db.collections.update_one(
            {"_id": ns},
            {"$set": {"tags": tags}}
        )
    except Exception as e:
        print(f"Failed to update collection tags for {ns}: {e}")

def assign_zones(admin, db, col_name, prefix_counts, shards):
    ns = f"OSM_DB.{col_name}"
    zones = [f"zone_{i}" for i in range(len(shards))]

    for i, shard in enumerate(shards):
        try:
            admin.command({"addShardToZone": shard, "zone": zones[i]})
        except Exception as e:
            if "already" not in str(e):
                print(f"Zone tagging error: {e}")

    total = sum(p['count'] for p in prefix_counts)
    per_zone = total / len(shards)

    zone_ranges = []
    zone_idx = 0
    count = 0
    start = prefix_counts[0]['_id']

    boundaries = []

    for i, p in enumerate(prefix_counts):
        count += p['count']
        last = (i == len(prefix_counts) - 1)
        if count >= per_zone or last:
            end = p['_id']
            zone_ranges.append((zones[zone_idx], start, end))
            boundaries.append(end)
            zone_idx = min(zone_idx + 1, len(shards) - 1)
            count = 0
            if i + 1 < len(prefix_counts):
                start = prefix_counts[i + 1]['_id']

    config_db = admin.client['config']
    chunks = list(config_db.chunks.find({"ns": ns}, {"min.geohash": 1}))
    existing_boundaries = set(chunk['min']['geohash'] for chunk in chunks)

    for zone, min_g, max_g in zone_ranges:
        min_key = {"geohash": min_g}
        max_key_str = max_g + "z" * (12 - len(max_g))
        max_key = {"geohash": max_key_str}

        try:
            retry_mongo_command(lambda: admin.command({
                "updateZoneKeyRange": ns,
                "min": min_key,
                "max": max_key,
                "zone": zone
            }))

            for b in boundaries:
                split_key_str = b + "a" * (12 - len(b))
                while split_key_str in existing_boundaries:
                    split_key_str = increment_string(split_key_str)
                split_key = {"geohash": split_key_str}
                try:
                    admin.command({"split": ns, "middle": split_key})
                except Exception as e:
                    if "is a boundary key" not in str(e):
                        print(f"Split error for key {split_key}: {e}")

            for zone_i, (z, start_g, end_g) in enumerate(zone_ranges):
                move_key = {"geohash": start_g}
                retry_mongo_command(lambda: admin.command({
                    "moveChunk": ns,
                    "find": move_key,
                    "to": shards[zone_i]
                }))

            print(f"{zone}: {min_g} → {max_key['geohash']}")

        except Exception as e:
            print(f"Zone operation error [{zone}]: {e}")

    # Uložení tagů do config.tags
    save_zone_tags(admin, ns, zone_ranges)
    # Aktualizace tagů v config.collections
    update_collection_tags(admin, ns, zone_ranges)

def assign_zones_transportation(admin, db, col_name, shards, global_prefixes):
    col = db[col_name]
    for try_prefix in range(MIN_PREFIX, MAX_PREFIX+1):
        prefix_counts = adaptive_prefix_counts(col, try_prefix, MAX_PREFIX)
        if len(prefix_counts) >= len(shards):
            print(f"Using prefix length {try_prefix} for '{col_name}'")
            assign_zones(admin, db, col_name, prefix_counts, shards)
            return
    print(f"Fallback: insufficient prefixes for '{col_name}', using global prefixes")
    assign_zones(admin, db, col_name, global_prefixes, shards)

# === MAIN ===

ensure_data_dir(DATA_PATH)
client = connect_mongo("mongodb://admin:nosql_2025@router01:27017/?authSource=admin")

with client:
    db = client['OSM_DB']
    admin = client['admin']

    import_json_files(db, DATA_PATH)
    shards = get_shards(admin)
    print(f"Shards: {shards}")

    global_prefix_counter = defaultdict(int)
    for fname in os.listdir(DATA_PATH):
        if not fname.endswith('.json'):
            continue
        cname = fname[:-5]
        col = db[cname]
        local_prefixes = adaptive_prefix_counts(col, MIN_PREFIX, MAX_PREFIX)
        for p in local_prefixes:
            global_prefix_counter[p['_id']] += p['count']

    global_prefixes = sorted(
        [{'_id': k, 'count': v} for k, v in global_prefix_counter.items()],
        key=lambda x: x['_id']
    )

    for fname in os.listdir(DATA_PATH):
        if not fname.endswith('.json'):
            continue
        cname = fname[:-5]
        col = db[cname]
        if col.estimated_document_count() == 0:
            print(f"'{cname}' is empty, skipping...")
            continue
        if cname == "transportation":
            assign_zones_transportation(admin, db, cname, shards, global_prefixes)
        else:
            assign_zones(admin, db, cname, global_prefixes, shards)

    print("Shard zone assignment complete.")
