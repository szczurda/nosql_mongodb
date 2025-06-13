sh.enableSharding("OSM_DB")
db = db.getSiblingDB("OSM_DB")

// --- Tourist Attractions ---
db.createCollection("tourist_attractions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "properties", "geometry", "geohash"],
      properties: {
        _id: { bsonType: "string" },
        type: { enum: ["Feature"] },
        properties: { bsonType: "object" },
        geometry: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point", "LineString", "Polygon", "MultiPolygon"] },
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
db.createCollection("accommodations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "properties", "geometry"],
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
          required: ["tourism", "geohash"],
          properties: {
            tourism: {
              enum: [
                "hotel",
                "hostel",
                "guest_house",
                "motel",
                "apartment",
                "camp_site",
                "caravan_site"
              ]
            },
            geohash: { bsonType: "string" }
          },
          additionalProperties: true
        }
      },
      additionalProperties: false
    }
  }
})
db.accommodations.createIndex({ geohash: 1 })
db.accommodations.createIndex({ geometry: "2dsphere" })
sh.shardCollection("OSM_DB.accommodations", { geohash: 1 })

// --- Transportation ---
db.createCollection("transportation", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "type", "properties", "geometry"],
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
          required: ["geohash"],
          properties: {
            geohash: { bsonType: "string" },
            highway: { enum: ["bus_stop"] },
            railway: { enum: ["station", "tram_stop", "subway_entrance"] },
            transportation: { enum: ["stop_position", "platform"] }
          },
          additionalProperties: true
        }
      },
      additionalProperties: false
    }
  }
})
db.transportation.createIndex({ geohash: 1 })
db.transportation.createIndex({ geometry: "2dsphere" })
sh.shardCollection("OSM_DB.transportation", { geohash: 1 })
