#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["protobuf", "gtfs-realtime-bindings"]
# ///

import sys

from google.protobuf import text_format
from google.transit import gtfs_realtime_pb2


def _get_english_string(translated_string: gtfs_realtime_pb2.TranslatedString) -> str:
    for translation in translated_string.translation:
        if translation.language == "en":
            return translation.text
    return ""


def _entity_sort_key(entity: gtfs_realtime_pb2.FeedEntity):
    return (
        entity.HasField("trip_update"),
        entity.HasField("vehicle"),
        entity.HasField("alert"),
        entity.vehicle.vehicle.label,
        entity.vehicle.vehicle.id,
        entity.trip_update.trip.route_id,
        entity.trip_update.trip.direction_id,
        entity.trip_update.trip.trip_id,
        entity.alert.severity_level,
        _get_english_string(entity.alert.header_text),
        _get_english_string(entity.alert.description_text),
        entity.alert.cause,
        entity.alert.effect,
        entity.alert.active_period[0].start if entity.alert.active_period else 0,
    )


def main():
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(sys.stdin.buffer.read())
    feed.entity.sort(key=_entity_sort_key)
    sys.stdout.write(text_format.MessageToString(feed))


if __name__ == "__main__":
    main()
