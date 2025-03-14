#!/bin/bash
set -exuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

curl -fL https://www.rtd-denver.com/files/gtfs/google_transit.zip | bsdtar -C static -xf -

for f in VehiclePosition.pb Alerts.pb; do
  curl -fL "https://www.rtd-denver.com/files/gtfs-rt/${f}" | ../gtfs_rt_stable_sort.py > "realtime/${f%.pb}.txtpb"
done