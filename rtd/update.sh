#!/bin/bash
set -exuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

curl -fL https://www.rtd-denver.com/files/gtfs/google_transit.zip | bsdtar -C static -xf -

for f in VehiclePosition.pb TripUpdate.pb Alerts.pb; do
  curl -fL "https://www.rtd-denver.com/files/gtfs-rt/${f}" | protoc --decode=transit_realtime.FeedMessage -I.. gtfs-realtime.proto > "realtime/${f%.pb}.txtpb"
done