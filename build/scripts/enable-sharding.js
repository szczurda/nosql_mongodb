sh.enableSharding("OSM_DB")
db = db.getSiblingDB("OSM_DB")

// --- Tourist Attractions ---
if (db.getCollectionNames().includes("tourist_attractions")) {
  db.tourist_attractions.drop()
}
db.createCollection("tourist_attractions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "properties", "geometry", "geohash"],
      properties: {
        _id: { bsonType: "string" },
        type: { enum: ["Feature"] },
        properties: {
          bsonType: "object",
          properties: {
            tourism: { bsonType: "string" },
            historic: { bsonType: "string" },
            man_made: { bsonType: "string" },
            natural: { bsonType: "string" }
          },
          additionalProperties: true
        },
        geometry: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: {
              enum: [
                "Point",
                "LineString",
                "Polygon",
                "MultiPolygon",
                "MultiLineString"
              ]
            },
            coordinates: { bsonType: "array" }
          },
          additionalProperties: false
        },
        geohash: { bsonType: "string" }
      },
      additionalProperties: false
    }
  }
})
db.tourist_attractions.createIndex({ geohash: 1 })
db.tourist_attractions.createIndex({ geometry: "2dsphere" })
sh.shardCollection("OSM_DB.tourist_attractions", { geohash: 1 })

// --- Accommodations ---
if (db.getCollectionNames().includes("accommodations")) {
  db.accommodations.drop()
}
db.createCollection("accommodations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "properties", "geometry", "geohash"],
      properties: {
        _id: { bsonType: "string" },
        type: { enum: ["Feature"] },
        geometry: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point", "LineString", "Polygon", "MultiPolygon"] },
            coordinates: { bsonType: "array" }
          },
          additionalProperties: false
        },
        properties: {
          bsonType: "object",
          required: ["tourism"],
          properties: {
            tourism: { bsonType: "string" }
          },
          additionalProperties: true
        },
        geohash: { bsonType: "string" }
      },
      additionalProperties: false
    }
  }
})
db.accommodations.createIndex({ geohash: 1 })
db.accommodations.createIndex({ geometry: "2dsphere" })
sh.shardCollection("OSM_DB.accommodations", { geohash: 1})

// --- Transportation ---
if (db.getCollectionNames().includes("transportation")) {
  db.transportation.drop()
}
db.createCollection("transportation", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "properties", "geometry", "geohash"],
      properties: {
        _id: { bsonType: "string" },
        type: { enum: ["Feature"] },
        geometry: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: {
              bsonType: "array",
              items: { bsonType: "double" },
              minItems: 2,
              maxItems: 2
            }
          },
          additionalProperties: false
        },
        properties: {
          bsonType: "object",
          properties: {
            highway: { bsonType: "string" },
            railway: { bsonType: "string" },
            transportation: { bsonType: "string" }
          },
          additionalProperties: true
        },
        geohash: { bsonType: "string" }
      },
      additionalProperties: false
    }
  }
})
db.transportation.createIndex({ geohash: 1 })
db.transportation.createIndex({ geometry: "2dsphere" })
sh.shardCollection("OSM_DB.transportation", { geohash: 1 })

