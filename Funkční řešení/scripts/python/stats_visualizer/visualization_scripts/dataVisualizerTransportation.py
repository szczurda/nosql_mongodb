import sys
import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import re
from collections import Counter

CATEGORY_TAGS = {
    "highway": {
        "bus_stop": "Autobusová zastávka",
    },
    "railway": {
        "station": "Vlaková stanice",
        "tram_stop": "Tramvajová zastávka",
        "subway_entrance": "Vchod do metra",
    },
    "public_transport": {
        "stop_position": "Zastávka veřejné dopravy",
        "platform": "Platforma veřejné dopravy",
    },
}

def detect_category(properties):
    for key, values in CATEGORY_TAGS.items():
        val = properties.get(key)
        if val in values:
            return values[val]
    return None

def load_data(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and "features" in data:
        features = data["features"]
    elif isinstance(data, list):
        features = data
    else:
        raise ValueError("Neočekávaný formát vstupu: očekávám GeoJSON s 'features' nebo pole objektů")

    records = []
    total_railway_stations = 0
    subway_stations_count = 0

    for feature in features:
        props = feature.get("properties", {})
        category = detect_category(props)
        if props.get("railway") == "station":
            total_railway_stations += 1
            if props.get("subway") == "yes":
                subway_stations_count += 1

        records.append({
            "category": category,
            "raw_properties": props,
            "has_name": "name" in props,
            "name": props.get("name"),
            "subway": props.get("subway"),
        })

    df = pd.DataFrame(records)
    return df, total_railway_stations, subway_stations_count

def plot_bar_chart(categories, output_path):
    counts = Counter(categories)
    total = sum(counts.values())
    sorted_items = sorted(counts.items(), key=lambda x: x[1]/total, reverse=True)
    labels, sizes = zip(*sorted_items)

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, sizes, color=plt.cm.tab20.colors[:len(labels)])
    ax.set_title("Počet typů veřejných dopravních zastávek v Česku", fontsize=16)
    ax.set_ylabel("Počet zastávek", fontsize=14)
    ax.set_xlabel("Typ zastávky", fontsize=14)
    ax.tick_params(axis='x', rotation=30, labelsize=12)

    for bar, count in zip(bars, sizes):
        height = bar.get_height()
        percent = count / total * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + total * 0.01,
            f"{count}\n({percent:.1f}%)",
            ha='center',
            va='bottom',
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8)
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Bar chart uložen do souboru: {output_path}")

def plot_railway_vs_subway(total_railway_stations, subway_stations_count, output_path):
    labels = ["Vlakové zastávky", "Stanice metra (subway=yes)"]
    counts = [total_railway_stations, subway_stations_count]

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, counts, color=["#1f77b4", "#ff7f0e"])
    ax.set_title("Porovnání počtu vlakových zastávek a stanic metra", fontsize=16)
    ax.set_ylabel("Počet", fontsize=14)
    ax.tick_params(axis='x', labelsize=12)

    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + max(counts)*0.01,
            f"{count}",
            ha='center',
            va='bottom',
            fontsize=12,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8)
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Railway vs Subway bar chart uložen do souboru: {output_path}")

def plot_wordcloud_names(df, output_path):
    from wordcloud import WordCloud
    names = df[df["has_name"] == True]["raw_properties"].apply(lambda p: p.get("name", ""))
    text = " ".join(names)
    text = re.sub(r'[^\w\s]', '', text)
    wordcloud = WordCloud(width=800, height=400, background_color='white', collocations=False).generate(text)
    plt.figure(figsize=(10,5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Wordcloud nejčastějších slov v názvech zastávek")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Wordcloud uložen do souboru: {output_path}")

def plot_osm_tags(df, top_n, output_path):
    all_keys = []
    for props in df["raw_properties"]:
        all_keys.extend(props.keys())
    counter = Counter(all_keys)
    most_common = counter.most_common(top_n)
    keys, counts = zip(*most_common)

    fig, ax = plt.subplots(figsize=(10,6))
    ax.bar(keys, counts, color='tab:purple')
    ax.set_title(f"Top {top_n} OSM tagů ve vlastnostech")
    ax.set_ylabel("Počet výskytů")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"OSM tags bar chart uložen do souboru: {output_path}")

def main(filepath, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    df, total_railway_stations, subway_stations_count = load_data(filepath)
    if df.empty:
        print("Data jsou prázdná nebo bez platných kategorií.")
        return

    plot_bar_chart(df['category'].dropna(), os.path.join(output_dir, "public_transport_bar.png"))
    plot_railway_vs_subway(total_railway_stations, subway_stations_count, os.path.join(output_dir, "railway_vs_subway.png"))
    plot_wordcloud_names(df, os.path.join(output_dir, "wordcloud_names.png"))
    plot_osm_tags(df, top_n=20, output_path=os.path.join(output_dir, "osm_tags.png"))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Použití: python dataVisualizerTransportation.py vstup.geojson vystupni_adresar")
        sys.exit(1)
    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    main(input_path, output_dir)
