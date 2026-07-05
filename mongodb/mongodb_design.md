# MongoDB Design — Metro Interstate Traffic Volume

## Design approach: denormalized, single collection, native time-series type

Unlike the relational design (normalized into 4 tables), MongoDB works best here as a
**single collection with embedded weather/holiday data**. Reasons:

- Queries on this dataset are almost always "give me records in this time range" or
  "aggregate by some attribute" — not multi-way joins. Embedding avoids `$lookup` costs.
- Weather/holiday attributes are small and read together with the traffic reading itself,
  so there's no write-amplification concern from denormalizing them.
- MongoDB 5.0+ has a **native time-series collection type**, purpose-built for exactly
  this shape of data (regular measurements over time from a small number of sources).
  It automatically buckets documents internally for storage/query efficiency.

### Collection creation

```javascript
db.createCollection('traffic_records', {
  timeseries: {
    timeField: 'date_time',
    metaField: 'metadata', // rarely-changing dimension: station info
    granularity: 'hours',
  },
});

db.traffic_records.createIndex({ date_time: 1 });
db.traffic_records.createIndex({ 'metadata.station_id': 1, date_time: 1 });
```

### Sample documents

```json
{
  "_id": ObjectId("665f1a2b3c4d5e6f7a8b9c01"),
  "date_time": ISODate("2012-10-02T09:00:00Z"),
  "metadata": {
    "station_id": "ATR-301",
    "station_name": "MN DoT ATR Station 301",
    "road_name": "I-94",
    "direction": "Westbound"
  },
  "weather": {
    "main": "Clouds",
    "description": "scattered clouds",
    "temp_kelvin": 288.28,
    "rain_1h": 0.0,
    "snow_1h": 0.0,
    "clouds_all": 40
  },
  "holiday": null,
  "traffic_volume": 5545
}
```

```json
{
  "_id": ObjectId("665f1a2b3c4d5e6f7a8b9c07"),
  "date_time": ISODate("2012-12-25T00:00:00Z"),
  "metadata": {
    "station_id": "ATR-301",
    "station_name": "MN DoT ATR Station 301",
    "road_name": "I-94",
    "direction": "Westbound"
  },
  "weather": {
    "main": "Snow",
    "description": "light snow",
    "temp_kelvin": 263.15,
    "rain_1h": 0.0,
    "snow_1h": 1.2,
    "clouds_all": 90
  },
  "holiday": "Christmas Day",
  "traffic_volume": 680
}
```

## Queries (run against the same 14-row sample used on the SQL side, for direct comparison)

### Query 1: Latest record

```javascript
db.traffic_records.find().sort({ date_time: -1 }).limit(1);
```

**Result:**

```json
{
  "date_time": "2013-06-15T17:00:00Z",
  "traffic_volume": 5980,
  "weather.main": "Rain"
}
```

Matches the SQL result exactly (2013-06-15 17:00:00, volume 5980, Rain).

### Query 2: Records by date range (October 2012)

```javascript
db.traffic_records
  .find({
    date_time: {
      $gte: ISODate('2012-10-01T00:00:00Z'),
      $lte: ISODate('2012-10-31T23:59:59Z'),
    },
  })
  .sort({ date_time: 1 });
```

**Result:** 6 documents, same rows as the SQL `BETWEEN` query
(2012-10-02 09:00 → 2012-10-03 08:00, volumes 5545, 4516, 4767, 5026, 6852, 6947).

### Query 3: Average traffic volume by weather condition (aggregation)

```javascript
db.traffic_records.aggregate([
  {
    $group: {
      _id: '$weather.main',
      avg_volume: { $avg: '$traffic_volume' },
      n_obs: { $sum: 1 },
    },
  },
  { $sort: { avg_volume: -1 } },
]);
```

**Result:**
| weather.main | avg_volume | n_obs |
|---|---|---|
| Clear | 6092.0 | 4 |
| Clouds | 6051.5 | 4 |
| Rain | 5373.5 | 2 |
| Mist | 890.0 | 1 |
| Snow | 807.3 | 3 |

Identical to the SQL `GROUP BY` result — confirms the two designs are logically equivalent.

### Query 4: Holiday vs. non-holiday average volume

```javascript
db.traffic_records.aggregate([
  {
    $group: {
      _id: { $cond: [{ $eq: ['$holiday', null] }, 'Non-holiday', 'Holiday'] },
      avg_volume: { $avg: '$traffic_volume' },
      n_obs: { $sum: 1 },
    },
  },
]);
```

**Result:**
| day_type | avg_volume | n_obs |
|---|---|---|
| Holiday | 828.0 | 4 |
| Non-holiday | 5932.1 | 10 |

Same numbers as the SQL side — holiday hours average ~828 vehicles vs. ~5,932 on
non-holidays in this sample, consistent with the well-known holiday dip in this dataset.

## Relational vs. MongoDB

- **Relational (SQL):** normalized, enforces referential integrity (FKs), avoids
  redundant weather/holiday text via lookup tables, better for strict schema
  validation and multi-table reporting joins.
- **MongoDB:** denormalized/embedded, no joins needed for the common read pattern,
  native time-series collection type gives storage and query optimizations
  purpose-built for this data shape, easier to evolve schema if new weather
  fields appear later.
- Both designs answer the same analytical questions and return identical numbers,
  which is worth stating explicitly as validation in your writeup.
