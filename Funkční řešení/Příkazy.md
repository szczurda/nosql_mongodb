## 7.1 Agregační funkce

### 7.1.1 – Počet ubytování dle města

```js
db.accommodations.aggregate([
  { $match: { "properties.addr:city": { $exists: true } } },
  { $group: { _id: "$properties.addr:city", count: { $sum: 1 } } },
  { $sort: { count: -1 } }
])
```

### 7.1.2 – Ubytování do 5 km od bodu

```js
db.accommodations.aggregate([
  {
    $geoNear: {
      near: { type: "Point", coordinates: [15.8325, 50.2092] },
      distanceField: "dist",
      maxDistance: 5000,
      spherical: true
    }
  },
  { $count: "count_within_5km" }
])
```

### 7.1.3 – Zastávky/stanice v okolí 10 km

```js
db.transportation.aggregate([
  {
    $geoNear: {
      near: { type: "Point", coordinates: [14.4378, 50.0755] },
      distanceField: "distance",
      maxDistance: 10000,
      spherical: true,
      query: {
        $or: [
          { "properties.highway": "bus_stop" },
          { "properties.railway": "station" }
        ]
      }
    }
  },
  {
    $group: {
      _id: {
        $cond: [
          { $eq: ["$properties.highway", "bus_stop"] },
          "bus_stop",
          "railway_station"
        ]
      },
      count: { $sum: 1 }
    }
  }
])
```

### 7.1.4 – Top 10 typů atrakcí

```js
db.tourist_attractions.aggregate([
  { $match: { "properties.tourism": { $ne: null } } },
  { $group: { _id: "$properties.tourism", count: { $sum: 1 } } },
  { $sort: { count: -1 } },
  { $limit: 10 }
])
```

### 7.1.5 – Průměrné počty pater dle typu budovy

```js
db.accommodations.aggregate([
  { $match: { "properties.building:levels": { $exists: true } } },
  { $addFields: { levelsNum: { $toInt: "$properties.building:levels" } } },
  { $group: { _id: "$properties.building", avgLevels: { $avg: "$levelsNum" } } },
  { $sort: { avgLevels: -1 } }
])
```

### 7.1.6

## Embedded dokumenty

### 7.2.1 – Zastávky se střechou a osvětlením

```js
db.transportation.aggregate([
  { $match: { "properties.shelter": "yes", "properties.lit": "yes" } },
  { $count: "count" }
])
```

### 7.2.2 – Zastávky podle laviček a košů

```js
db.transportation.aggregate([
  {
    $group: {
      _id: {
        bench: { $ifNull: ["$properties.bench", "no"] },
        bin: { $ifNull: ["$properties.bin", "no"] }
      },
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      bench: "$_id.bench",
      bin: "$_id.bin",
      count: 1
    }
  }
])
```

### 7.2.3 – Vkladatelé turistických atrakcí

```js
db.tourist_attractions.aggregate([
  { $match: { "properties.created_by": { $exists: true } } },
  {
    $group: {
      _id: "$properties.created_by",
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      created_by: "$_id",
      count: 1,
      _id: 0
    }
  }
])
```

### 7.2.4 – Atrakce s wikidaty

```js
db.tourist_attractions.aggregate([
  {
    $group: {
      _id: {
        hasWikidata: {
          $cond: [{ $ifNull: ["$properties.wikidata", false] }, "yes", "no"]
        }
      },
      count: { $sum: 1 }
    }
  },
  {
    $project: {
      _id: 0,
      hasWikidata: "$_id.hasWikidata",
      count: 1
    }
  }
])
```

### 7.2.5 – Průměrná nadmořská výška atrakcí

```js
db.tourist_attractions.aggregate([
  { $match: { "properties.ele": { $exists: true } } },
  { $match: { "properties.ele": { $regex: /^[0-9]+(\.[0-9]+)?$/ } } },
  {
    $group: {
      _id: null,
      avgElevation: { $avg: { $toDouble: "$properties.ele" } }
    }
  },
  { $project: { _id: 0, avgElevation: 1 } }
])
```

### 7.2.6 – Normalizace a výskyt hvězdiček

```js
db.accommodations.aggregate([
  { $match: { "properties.stars": { $exists: true } } },
  {
    $addFields: {
      stars_normalized: {
        $replaceAll: {
          input: "$properties.stars",
          find: ",",
          replacement: "."
        }
      }
    }
  },
  {
    $match: {
      stars_normalized: { $regex: /^[1-5](\.[0-9])?$/ }
    }
  },
  {
    $group: {
      _id: "$stars_normalized",
      count: { $sum: 1 }
    }
  },
  { $sort: { _id: 1 } }
])
```

## 7.3 Práce s daty – Insert, Update, Delete, Merge

### 7.3.1 – Vložení nové atrakce

```js
db.tourist_attractions.insertOne({
  type: "Feature",
  properties: {
    tourism: "museum",
    name: "Nové muzeum",
    wheelchair: "yes"
  },
  geometry: {
    type: "Point",
    coordinates: [14.4208, 50.087]
  },
  _id: "node/8888888888",
  geohash: "u2f6k4r2t"
})
```

### 7.3.2 – Mazání ubytování podle prefixu geohashe

```js
db.accommodations.deleteMany({
  geohash: { $regex: "^u2ex" }
})
```

### 7.3.3 – Aktualizace dostupnosti podle bezbariérovosti

```js
db.tourist_attractions.updateMany(
  { "properties.wheelchair": "yes" },
  { $set: { "properties.accessible": "yes" } }
)
```

### 7.3.4 – Merge hotelů do nové kolekce

```js
db.accommodations.aggregate([
  { $match: { "properties.tourism": "hotel" } },
  {
    $merge: {
      into: "hotels_summary",
      on: "_id",
      whenMatched: "merge",
      whenNotMatched: "insert"
    }
  }
])
```

### 7.3.5 – Zvýšení hvězdiček (max 5)

```js
db.accommodations.updateMany(
  {
    "properties.stars": {
      $exists: true,
      $regex: /^[1-5](,[0-9])?$/
    }
  },
  [
    {
      $set: {
        "properties.stars": {
          $let: {
            vars: {
              starsNum: {
                $toDouble: {
                  $replaceAll: {
                    input: "$properties.stars",
                    find: ",",
                    replacement: "."
                  }
                }
              }
            },
            in: {
              $toString: {
                $min: [5, { $add: ["$$starsNum", 1] }]
              }
            }
          }
        }
      }
    }
  ]
)
```

### 7.3.6 – Spojení hotelů s atrakcemi podle geohashe

```js
db.accommodations.aggregate([
  {
    $match: {
      "properties.tourism": "hotel",
      geohash: { $exists: true }
    }
  },
  {
    $project: {
      _id: 1,
      name: "$properties.name",
      stars: "$properties.stars",
      geohash_prefix: { $substr: ["$geohash", 0, 6] }
    }
  },
  {
    $lookup: {
      from: "tourist_attractions",
      let: { ghash: "$geohash_prefix" },
      pipeline: [
        {
          $project: {
            name: "$properties.name",
            type: "$properties.tourism",
            fee: "$properties.fee",
            geohash_prefix: { $substr: ["$geohash", 0, 6] }
          }
        },
        {
          $match: {
            $expr: { $eq: ["$geohash_prefix", "$$ghash"] }
          }
        }
      ],
      as: "nearby_attractions"
    }
  },
  { $limit: 100 },
  {
    $merge: {
      into: "accommodation_attractions_summary",
      whenMatched: "merge",
      whenNotMatched: "insert"
    }
  }
])
```

## 7.4 Indexy a výkon

### 7.4.1 – Index pro hotely a geohash

```js
db.accommodations.createIndex({ "properties.tourism": 1, geohash: 1 })
```

### 7.4.2 – Explain dotazu

```js
db.accommodations.aggregate([
  { $match: { "properties.tourism": "hotel" } }
]).explain("executionStats")
```

### 7.4.3 – Dotaz s hintem

```js
db.accommodations.find({
  geohash: { $regex: "^u2ewxuucx" }
}).hint({ geohash: 1 })
```

### 7.4.4 – 2dsphere index

```js
db.tourist_attractions.createIndex({ geometry: "2dsphere" })
```

### 7.4.5 – Analýza shard key

```js
db.adminCommand({
  analyzeShardKey: "OSM_DB.tourist_attractions",
  key: { geohash: 1 }
})
```

### 7.4.6 – Wildcard index na vlastnosti

```js
db.transportation.createIndex({ "properties.$**": 1 })
```

## 7.5 Cluster a konfigurace

### 7.5.1 – Stav shardingu

```js
sh.status()
```

### 7.5.2 – Rozložení dat

```js
sh.getShardedDataDistribution()
```

### 7.5.3 – Stav balanceru

```js
sh.getBalancerState()
```

### 7.5.4 – Konfigurační parametry

```js
db.adminCommand({ getCmdLineOpts: 1 })
```

### 7.5.5 – Chunky podle shardů

```js
use config
db.chunks.aggregate([
  { $group: { _id: "$shard", count: { $sum: 1 } } }
])
```

### 7.5.6 – Výpis shardů

```js
use config
db.adminCommand({ listShards: 1 })
```
