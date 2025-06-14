import sys
import os
import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from collections import Counter
from shapely.geometry import shape
from wordcloud import WordCloud
import re
import seaborn as sns

# --- Funkce pro načtení a přípravu dat ---

def load_osm_data(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and "features" in data:
        features = data["features"]
    elif isinstance(data, list):
        features = data
    else:
        raise ValueError("Neočekávaný formát vstupu: očekávám GeoJSON s 'features' nebo pole objektů")

    records = []
    for feat in features:
        props = feat.get("properties", {})
        geom = feat.get("geometry", {})
        coords = None
        if geom.get("type") == "Point":
            coords = geom.get("coordinates")

        records.append({
            **props,
            "_geometry_type": geom.get("type"),
            "_coordinates": coords
        })

    df = pd.DataFrame(records)
    return df, features

# --- Vizualizace ---

def plot_category_counts(df, output_dir):
    # Počet různých hodnot v tagu "highway", "railway" a "public_transport" pokud existují
    tags = ["highway", "railway", "public_transport"]
    all_cats = []
    for tag in tags:
        if tag in df.columns:
            all_cats.extend(df[tag].dropna().astype(str).tolist())

    if not all_cats:
        print("Žádné kategorie z tagů highway, railway, public_transport.")
        return

    counts = Counter(all_cats)
    labels, values = zip(*counts.most_common())
    total = sum(values)

    plt.figure(figsize=(12,6))
    bars = plt.bar(labels, values, color=plt.cm.tab20.colors[:len(labels)])
    plt.title("Počet prvků podle kategorií OSM tagů (highway, railway, public_transport)")
    plt.ylabel("Počet")
    plt.xticks(rotation=45, ha="right")

    for bar, val in zip(bars, values):
        plt.text(bar.get_x() + bar.get_width()/2, val + total*0.01, f"{val}\n({val/total*100:.1f}%)",
                 ha='center', fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.7))

    plt.tight_layout()
    filename = "category_counts.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=300)
    plt.close()
    print(f"Uloženo: {filename}")

def plot_name_length_histogram(df, output_dir):
    if "name" not in df.columns:
        print("Tag 'name' není v datech, přeskočeno histogram délky názvů.")
        return
    lengths = df["name"].dropna().map(len)
    plt.figure(figsize=(8,5))
    plt.hist(lengths, bins=30, color='tab:purple', alpha=0.7)
    plt.title("Distribuce délky názvů prvků")
    plt.xlabel("Délka názvu (počet znaků)")
    plt.ylabel("Počet prvků")
    plt.tight_layout()
    filename = "name_length_histogram.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=300)
    plt.close()
    print(f"Uloženo: {filename}")

def plot_numeric_tag_boxplots(df, output_dir, max_tags=5):
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) == 0:
        print("Žádné numerické tagy, boxplot přeskočen.")
        return

    for col in numeric_cols[:max_tags]:
        plt.figure(figsize=(6,4))
        df[col].dropna().plot.box()
        plt.title(f"Boxplot hodnot tagu '{col}'")
        plt.ylabel(col)
        plt.tight_layout()
        filename = f"boxplot_{col}.png"
        plt.savefig(os.path.join(output_dir, filename), dpi=300)
        plt.close()
        print(f"Uloženo: {filename}")

def plot_numeric_correlation_heatmap(df, output_dir):
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) < 2:
        print("Nedostatek numerických tagů pro korelační heatmapu.")
        return
    corr = df[numeric_cols].corr()
    plt.figure(figsize=(8,6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", vmin=-1, vmax=1)
    plt.title("Korelační matice numerických tagů")
    plt.tight_layout()
    filename = "numeric_tags_correlation_heatmap.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=300)
    plt.close()
    print(f"Uloženo: {filename}")

def plot_geometry_type_counts(features, output_dir):
    geom_types = [feat.get("geometry", {}).get("type") for feat in features]
    counts = Counter(geom_types)
    labels, values = zip(*counts.items())

    plt.figure(figsize=(8,5))
    plt.bar(labels, values, color='tab:cyan')
    plt.title("Počet prvků podle typu geometrie")
    plt.xlabel("Typ geometrie")
    plt.ylabel("Počet prvků")
    plt.tight_layout()
    filename = "geometry_type_counts.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=300)
    plt.close()
    print(f"Uloženo: {filename}")

def plot_wordcloud_for_tag(df, tag="amenity", output_dir="output"):
    if tag not in df.columns:
        print(f"Tag '{tag}' není v datech, wordcloud přeskočen.")
        return
    text = " ".join(df[tag].dropna().astype(str))
    if not text.strip():
        print(f"Tag '{tag}' je prázdný, wordcloud přeskočen.")
        return

    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    plt.figure(figsize=(10,5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.title(f"Wordcloud hodnot tagu '{tag}'")
    plt.tight_layout()
    filename = f"wordcloud_{tag}.png"
    plt.savefig(os.path.join(output_dir, filename), dpi=300)
    plt.close()
    print(f"Uloženo: {filename}")

# --- Main ---

def main(filepath, output_dir="output"):
    os.makedirs(output_dir, exist_ok=True)
    print(f"Načítám data ze souboru: {filepath}")
    df, features = load_osm_data(filepath)

    print(f"Celkem načteno prvků: {len(df)}")

    plot_category_counts(df, output_dir)
    plot_name_length_histogram(df, output_dir)
    plot_numeric_tag_boxplots(df, output_dir)
    plot_numeric_correlation_heatmap(df, output_dir)
    plot_geometry_type_counts(features, output_dir)
    plot_wordcloud_for_tag(df, tag="amenity", output_dir=output_dir)

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Použití: python osm_general_analysis.py vstup.geojson [output_dir]")
        sys.exit(1)
    filepath = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) == 3 else "output"
    main(filepath, outdir)
