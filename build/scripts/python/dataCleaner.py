import json
import geohash2
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon, MultiLineString

def compute_geohash(geometry):
    try:
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")
        if geom_type in {"Point"}:
            lon, lat = coords
        else:
            # Pro složitější geometrie je použitý centroid
            geo_shape = shape(geometry)
            centroid: Point = geo_shape.centroid
            lon, lat = centroid.x, centroid.y
        return geohash2.encode(lat, lon, precision=9)
    except Exception:
        return None

def clean_osm_data_for_mongo(features):
    seen_ids = set()
    cleaned = []
    removed_count = 0

    for feature in features:
        osm_id = feature.get("id")
        if osm_id is None:
            removed_count += 1
            continue

        geometry = feature.get("geometry", {})
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")

        if coords is None:
            removed_count += 1
            continue

        if geom_type == "LineString" and len(coords) < 2:
            removed_count += 1
            continue
        if geom_type == "Polygon" and not any(len(ring) >= 4 for ring in coords):
            removed_count += 1
            continue
        if geom_type == "MultiPolygon" and not any(
                any(len(ring) >= 4 for ring in polygon) for polygon in coords
        ):
            removed_count += 1
            continue

        if osm_id in seen_ids:
            removed_count += 1
            continue
        seen_ids.add(osm_id)

        feature["_id"] = osm_id
        feature.pop("id", None)

        props = feature.get("properties", {})
        props.pop("@id", None)

        # Odstranit "name:*"
        for k in list(props.keys()):
            if k.startswith("name:"):
                props.pop(k)

        # Odstranit "name:*" i v @relations.reltags
        if "@relations" in props:
            for rel in props["@relations"]:
                reltags = rel.get("reltags", {})
                for k in list(reltags.keys()):
                    if k.startswith("name:"):
                        reltags.pop(k)

        # Vypočti geohash
        geohash = compute_geohash(geometry)
        if geohash:
            props["geohash"] = geohash
        else:
            removed_count += 1
            continue

        cleaned.append(feature)

    return cleaned, removed_count


def main(input_file, output_file):
    with open(input_file, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "features" in data:
        features = data["features"]
    elif isinstance(data, list):
        features = data
    else:
        print("Chyba: vstup není validní GeoJSON s polem 'features' nebo pole feature.")
        return

    cleaned, removed_count = clean_osm_data_for_mongo(features)

    output_data = {"type": "FeatureCollection", "features": cleaned} if isinstance(data, dict) else cleaned

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Počet původních feature: {len(features)}")
    print(f"Počet odstraněných feature: {removed_count}")
    print(f"Počet výsledných feature: {len(cleaned)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Použití: python dataCleaner.py vstup.geojson vystup.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    main(input_file, output_file)
