import sys
import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import re
from collections import Counter
from wordcloud import WordCloud

# Definice kategorií podle OSM tagů pro turistické atrakce
CATEGORY_TAGS = {
    "tourism": {
        "attraction": "Atrakcí",
        "viewpoint": "Vyhlídka",
        "museum": "Muzeum",
        "artwork": "Umělecké dílo",
        "gallery": "Galerie",
        "theme_park": "Zábavní park",
        "zoo": "ZOO",
    },
    "historic": {
        None: "Historická památka",  # pokud je tag historic bez hodnoty nebo s libovolnou hodnotou
    },
    "man_made": {
        "tower": "Věž",
    },
    "natural": {
        "peak": "Vrchol",
    }
}

def detect_category(tags):
    if not tags:
        return None
    for key, val_map in CATEGORY_TAGS.items():
        if key in tags:
            v = tags.get(key)
            if v in val_map:
                return val_map[v]
            # zvlášť pro historic, pokud tam je tag historic (bez ohledu na hodnotu)
            if key == "historic" and v is not None:
                return val_map[None]
    return None

def load_data_flexible(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "features" in data:
            features = data["features"]
        elif "elements" in data:
            features = data["elements"]
        else:
            raise ValueError("Neočekávaný formát vstupu, chybí 'features' i 'elements'")
    elif isinstance(data, list):
        features = data
    else:
        raise ValueError("Neočekávaný formát vstupu, očekávám dict nebo list")

    records = []
    for feature in features:
        # GeoJSON má vlastnosti v "properties", Overpass v "tags"
        if "properties" in feature:
            tags = feature.get("properties", {})
        else:
            tags = feature.get("tags", {})

        category = detect_category(tags)
        records.append({
            "category": category,
            "tags": tags,
            "has_name": "name" in tags,
            "name": tags.get("name", ""),
            "geometry_type": feature.get("geometry", {}).get("type", "") if "geometry" in feature else feature.get("type", ""),
            "id": feature.get("id", ""),
        })

    df = pd.DataFrame(records)
    return df

def plot_category_distribution(df, output_path):
    categories = df['category'].dropna()
    if categories.empty:
        print("Nebyly nalezeny žádné platné kategorie pro vizualizaci.")
        return

    counts = Counter(categories)
    total = sum(counts.values())
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    labels, sizes = zip(*sorted_items)

    fig, ax = plt.subplots(figsize=(10,6))
    bars = ax.bar(labels, sizes, color=plt.cm.tab20.colors[:len(labels)])
    ax.set_title("Počet typů turistických atrakcí v Česku", fontsize=16)
    ax.set_ylabel("Počet prvků", fontsize=14)
    ax.set_xlabel("Kategorie", fontsize=14)
    ax.tick_params(axis='x', rotation=30, labelsize=12)

    for bar, count in zip(bars, sizes):
        height = bar.get_height()
        percent = count / total * 100
        ax.text(
            bar.get_x() + bar.get_width()/2,
            height + total*0.01,
            f"{count}\n({percent:.1f}%)",
            ha='center',
            va='bottom',
            fontsize=11,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.8)
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Graf kategorií uložen do: {output_path}")

def plot_name_wordcloud(df, output_path):
    names = df[df["has_name"]]["name"]
    if names.empty:
        print("Nejsou k dispozici žádná jména pro wordcloud.")
        return

    text = " ".join(names)
    text = re.sub(r'[^\w\s]', '', text)
    wordcloud = WordCloud(width=800, height=400, background_color='white', collocations=False).generate(text)

    plt.figure(figsize=(10,5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title("Wordcloud nejčastějších slov v názvech atrakcí")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Wordcloud uložen do: {output_path}")

def plot_top_osm_tags(df, top_n, output_path):
    all_keys = []
    for tags in df["tags"]:
        all_keys.extend(tags.keys())

    counter = Counter(all_keys)
    most_common = counter.most_common(top_n)
    if not most_common:
        print("Nenalezeny žádné OSM tagy pro vizualizaci.")
        return

    keys, counts = zip(*most_common)
    fig, ax = plt.subplots(figsize=(10,6))
    ax.bar(keys, counts, color='tab:green')
    ax.set_title(f"Top {top_n} nejčastějších OSM tagů")
    ax.set_ylabel("Počet výskytů")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Graf OSM tagů uložen do: {output_path}")

def main(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Načítám data ze souboru: {input_file}")
    df = load_data_flexible(input_file)
    if df.empty:
        print("Data jsou prázdná, není co vizualizovat.")
        return

    plot_category_distribution(df, os.path.join(output_dir, "category_distribution.png"))
    plot_name_wordcloud(df, os.path.join(output_dir, "name_wordcloud.png"))
    plot_top_osm_tags(df, top_n=20, output_path=os.path.join(output_dir, "top_osm_tags.png"))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Použití: python dataVisualizerTouristAttractions.py vstup.json vystupní_adresář")
        sys.exit(1)
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    main(input_file, output_dir)
