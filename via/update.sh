#!/bin/bash
set -exuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

curl -fL https://passio3.com/viaboulder/passioTransit/gtfs/google_transit.zip | bsdtar -C static -xf -
curl -fL "https://passio3.com/viaboulder/passioTransit/gtfs/realtime/vehiclePositions" | ../gtfs_rt_stable_sort.py > "realtime/VehiclePosition.txtpb"
curl -fL "https://passio3.com/viaboulder/passioTransit/gtfs/realtime/serviceAlerts" | ../gtfs_rt_stable_sort.py > "realtime/Alerts.txtpb"
