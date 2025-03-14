# GTFS Data Snapshots for Denver-area transit

This is a git repo with GTFS (realtime and schedules) data updated on a cron job
running every 5 minutes.  It could be useful for the purpose of analyzing data
over time, or recalling historical data.

At the moment it just has RTD data, but this may change later.

Structure:

```
├── <agency>
│   ├── LICENSE.md     # READ!  This data comes from an agency which may have license usage restrictions.
│   ├── realtime
│   │   ├── Alerts.txtpb
│   │   └── VehiclePosition.txtpb
│   ├── static
│   │   ├── agency.txt
│   │   ├── ...
│   │   └── trips.txt
│   └── update.sh     # Agency-specific script to download GTFS data.
└── ...
```

Have fun!
