import sys
import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import re
from collections import Counter
from wordcloud import WordCloud

ACCOMMODATION_TYPES = {
    "hotel": "Hotel",
    "motel": "Motel",
    "guest_house": "Penzion / Guest house",
    "hostel": "Hostel",
    "apartment": "Apartmán",
    "camp_site": "Kemp",
    "caravan_site": "Karavan kemp",
    "chalet": "Chata",
    "bungalow": "Bungalov",
}

def detect_accommodation(tags):
    if not tags:
        return None
    if tags.get("tourism") in ACCOMMODATION_TYPES:
        return ACCOMMODATION_TYPES[tags.get("tourism")]
    return None

def load_data(filepath):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "features" in data:
            features = data["features"]
        elif "elements" in data:
            features = data["elements"]
        else:
            raise ValueError("Neočekávaný formát vstupu - chybí 'features' i 'elements'")
    elif isinstance(data, list):
        features = data
    else:
        raise ValueError("Neočekávaný formát vstupu")

    records = []
    for feature in features:
        tags = feature.get("properties") or feature.get("tags") or {}
        category = detect_accommodation(tags)
        records.append({
            "category": category,
            "tags": tags,
            "has_name": "name" in tags,
            "name": tags.get("name", ""),
        })

    df = pd.DataFrame(records)
    return df

def plot_category_distribution(df, output_path):
    categories = df['category'].dropna()
    if categories.empty:
        print("Žádné kategorie ubytování k vizualizaci.")
        return

    counts = Counter(categories)
    sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    labels, sizes = zip(*sorted_items)

    plt.figure(figsize=(10,6))
    bars = plt.bar(labels, sizes, color=plt.cm.Paired.colors[:len(labels)])
    plt.title("Počet typů ubytování v datech")
    plt.ylabel("Počet záznamů")
    plt.xticks(rotation=30, ha="right")

    for bar, size in zip(bars, sizes):
        plt.text(bar.get_x() + bar.get_width()/2, size, str(size), ha='center', va='bottom')

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
    plt.title("Wordcloud nejčastějších slov v názvech ubytování")
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
    plt.figure(figsize=(10,6))
    plt.bar(keys, counts, color='slateblue')
    plt.title(f"Top {top_n} nejčastějších OSM tagů v ubytování")
    plt.ylabel("Počet výskytů")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Graf OSM tagů uložen do: {output_path}")

def main(input_file, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Načítám data ze souboru: {input_file}")
    df = load_data(input_file)
    if df.empty:
        print("Data jsou prázdná, není co analyzovat.")
        return

    plot_category_distribution(df, os.path.join(output_dir, "accommodation_categories.png"))
    plot_name_wordcloud(df, os.path.join(output_dir, "name_wordcloud.png"))
    plot_top_osm_tags(df, top_n=20, output_path=os.path.join(output_dir, "top_osm_tags.png"))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Použití: python dataVisualizerAccommodations.py vstup.json vystupní_adresář")
        sys.exit(1)
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    main(input_file, output_dir)
