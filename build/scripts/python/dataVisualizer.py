import folium
import json

# Načti GeoJSON data z .geojson souboru
with open('data.geojson', 'r', encoding='utf-8') as f:
    geojson = json.load(f)

# Vytvoření mapy, střed a zoom nastav podle dat (tady ručně)
m = folium.Map(location=[49.0, 15.0], zoom_start=7)

def get_color(feature):
    # Příklad: barva podle typu budovy
    btype = feature['properties'].get('building', '').lower()
    if btype == 'hotel':
        return 'red'
    elif btype == 'guest_house':
        return 'green'
    elif btype == 'yes':
        return 'blue'
    else:
        return 'gray'

# Projdeme všechny feature a přidáme je na mapu
for feature in geojson['features']:
    geom = feature['geometry']
    props = feature['properties']

    color = get_color(feature)
    popup_text = f"{props.get('name', 'bez názvu')}<br>Typ: {props.get('building', 'není')}"

    # Podle typu geometrie přidáme jinak
    if geom['type'] == 'Polygon':
        folium.Polygon(
            locations=[[(coord[1], coord[0]) for coord in ring] for ring in geom['coordinates']],
            color=color,
            fill=True,
            fill_color=color,
            popup=popup_text
        ).add_to(m)

    elif geom['type'] == 'Point':
        folium.Marker(
            location=[geom['coordinates'][1], geom['coordinates'][0]],
            popup=popup_text,
            icon=folium.Icon(color=color)
        ).add_to(m)
    # Přidej další typy, pokud chceš (MultiPolygon, LineString...)

# Ulož mapu
m.save('mapa_vizualizace.html')
