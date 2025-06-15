import json
import pandas as pd
import matplotlib.pyplot as plt
from pprint import pprint
import sys
import os
from collections import Counter
from shapely.geometry import shape, Polygon, Point, LineString, MultiPolygon, MultiLineString, GeometryCollection

USELESS_KEYS = {
    'note', 'fixme', 'comment', 'source', 'attribution',
    'created_by', 'changeset', 'timestamp', 'version', 'user', 'uid',
    'osm_id', 'metadata', 'history', 'note:en', 'note:fr'
}

USELESS_VALUES = {
    "", "unknown", "todo", "n/a", "-", "none", "null", "undefined", "false", "0",
    None, False, 0, "yes", "true", "1"
}

def is_useful_properties(props):
    if not props or not isinstance(props, dict):
        return False
    for k, v in props.items():
        key_lower = k.lower()
        if key_lower in USELESS_KEYS:
            continue
        val_str = str(v).strip().lower() if v is not None else ""
        if val_str in USELESS_VALUES:
            continue
        if val_str and len(val_str) > 1:
            return True
    return False

def analyze_geojson(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        features = json.load(f)

    if not isinstance(features, list):
        raise ValueError("Expected input to be a JSON array of GeoJSON features.")

    total = len(features)
    no_geom = 0
    bad_geom = 0
    no_props = 0
    useful_props = 0
    empty_features = 0

    geom_type_counter = Counter()
    osm_type_counter = Counter()
    invalid_geom_reasons_counter = Counter()

    details = []

    for idx, feature in enumerate(features):
        geom_dict = feature.get("geometry")
        props = feature.get("properties", {})
        fid = feature.get("_id", feature.get("id", f"idx_{idx}"))

        osm_type = None
        if isinstance(fid, str) and '/' in fid:
            osm_type = fid.split('/')[0]
        osm_type_counter[osm_type] += 1

        geom = None
        geom_issue_causes = []

        if geom_dict:
            try:
                geom = shape(geom_dict)
                geom_type_counter[geom.geom_type] += 1
            except Exception:
                geom = None
                geom_issue_causes.append("geom_invalid_format")
        else:
            geom_issue_causes.append("geom_missing")

        if geom is None:
            no_geom += 1
        else:
            if not geom.is_valid:
                geom_issue_causes.append("geom_invalid")
            if isinstance(geom, Point):
                coords = list(geom.coords)[0]
                lon, lat = coords[0], coords[1]
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    geom_issue_causes.append("geom_point_out_of_bounds")
                if abs(lon) < 1e-7 and abs(lat) < 1e-7:
                    geom_issue_causes.append("geom_point_at_origin")

        geom_ok = (len(geom_issue_causes) == 0)
        if not geom_ok:
            bad_geom += 1
            for cause in geom_issue_causes:
                invalid_geom_reasons_counter[cause] += 1
            print(f"Removed feature due to geometry issues: {fid} causes: {geom_issue_causes}")

        props_ok = is_useful_properties(props)
        if props_ok:
            useful_props += 1
        else:
            no_props += 1

        causes = []
        if geom_issue_causes:
            causes.extend(geom_issue_causes)
        if not props_ok:
            causes.append("no_useful_props")

        empty = (not geom_ok) and (not props_ok)
        if empty:
            empty_features += 1

        details.append({
            "feature_id": fid,
            "osm_type": osm_type,
            "geometry_type": geom_dict.get("type") if geom_dict else None,
            "empty": empty,
            "causes": ", ".join(causes) if causes else "none",
        })

    summary = {
        "Total Features": total,
        "No Geometry": no_geom,
        "Invalid Geometry": bad_geom,
        "No Useful Properties": no_props,
        "Useful Properties": useful_props,
        "Empty Features (bad geom AND no useful props)": empty_features,
        "Percent Empty Features": round(100 * empty_features / total, 2) if total else 0,
        "Geometry Types Counts": dict(geom_type_counter),
        "OSM Types Counts": dict(osm_type_counter),
        "Invalid Geometry Reasons": dict(invalid_geom_reasons_counter),
    }
    return summary, details

def visualize_pie(counter_dict, title, output_file):
    if not counter_dict:
        print(f"No data to plot for {title}")
        return
    total = sum(counter_dict.values())
    labels, values = zip(*sorted(counter_dict.items(), key=lambda x: -x[1]))
    labels_pct = [f"{label} ({count}, {count / total * 100:.1f}%)" for label, count in zip(labels, values)]

    colors = plt.get_cmap('tab20').colors  # barevná paleta

    plt.figure(figsize=(7,7))
    wedges, _ = plt.pie(values, labels=[None]*len(values), colors=colors[:len(values)], startangle=140)
    plt.title(title)

    # legenda vedle koláče s odpovídající barvou a popisky
    plt.legend(wedges, labels_pct, title="Categories", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)

    plt.tight_layout()
    plt.savefig(output_file, bbox_inches="tight")
    plt.close()


def visualize_summary(summary, output_prefix):
    labels = [
        "No Geometry",
        "Invalid Geometry",
        "No Useful Properties",
        "Useful Properties",
        "Empty Features"
    ]
    values = [
        summary["No Geometry"],
        summary["Invalid Geometry"],
        summary["No Useful Properties"],
        summary["Useful Properties"],
        summary["Empty Features (bad geom AND no useful props)"]
    ]

    colors = ['#e74c3c', '#f39c12', '#d35400', '#27ae60', '#34495e']

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, values, color=colors)
    plt.title("GeoJSON Features Usefulness Analysis")
    plt.ylabel("Count")
    plt.xticks(rotation=25)
    plt.tight_layout()

    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, height, str(height), ha='center', va='bottom')

    plt.savefig(f"{output_prefix}_usefulness_analysis.png")
    plt.close()

def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py path/to/features.json")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    summary, details = analyze_geojson(file_path)
    pprint(summary)

    base = os.path.splitext(os.path.basename(file_path))[0]
    output_prefix = f"{base}_usefulness"

    pd.DataFrame([summary]).to_csv(f"{output_prefix}.csv", index=False)
    pd.DataFrame(details).to_csv(f"{output_prefix}_details.csv", index=False)

    visualize_summary(summary, output_prefix)
    visualize_pie(summary["Geometry Types Counts"], "Geometry Types Distribution", f"{output_prefix}_geometry_types_pie.png")
    visualize_pie(summary["OSM Types Counts"], "OSM Types Distribution", f"{output_prefix}_osm_types_pie.png")

if __name__ == "__main__":
    main()
