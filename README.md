# GTFS Data Snapshots for Denver-area transit

This is a git repo with GTFS (realtime vehicle positions, alerts, and schedules)
data updated on a cron job running every 5 minutes.  It could be useful for the
purpose of analyzing data over time, or recalling historical data.

Structure:

```
├── <agency>
│   ├── LICENSE.md     # READ!  This data comes from an agency which may have license usage restrictions.
│   ├── realtime
│   │   ├── alerts
│   │   │   └── <entity_id>.txtpb
│   │   └── vehicles
│   │       └── <vehicle_label>.txtpb
│   └── static
│       ├── agency.txt
│       ├── ...
│       └── trips.txt
└── ...
```

This is the `v2` branch, which is the second iteration of the file layout.  It's
an improvement from `v1`, which stored the GTFS protos without splitting by
entity.  A few older days of historical data can be found on the `v1` branch,
but otherwise it's not worth fetching.

Agencies:

* `rtd`: RTD Denver
* `via`: Via Mobility Boulder (HOP and Lyons Flyer)

Have fun!
