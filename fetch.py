#!/usr/bin/env -S uv run

import asyncio
import io
import dataclasses
import pathlib
from typing import Annotated, Optional
import zipfile
import csv

import aiofiles
import aiofiles.os
import aiohttp
import github_action_utils as gha
import async_typer
from google.protobuf import text_format
from google.transit import gtfs_realtime_pb2
import typer


app = async_typer.AsyncTyper()
commit_lock = asyncio.Lock()
HERE = pathlib.Path(__file__).resolve().parent


def csv_normalize(content: bytes) -> bytes:
    """Sort CSV rows and clean up any quoting discrepancies."""
    reader = csv.reader(io.StringIO(content.decode("utf-8")))
    try:
        header_row = next(reader)
    except StopIteration:
        return b""
    rows = sorted(reader)
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(header_row)
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


@dataclasses.dataclass
class FileTracker:
    seen_files: set[pathlib.Path] = dataclasses.field(default_factory=set)
    changed_files: set[pathlib.Path] = dataclasses.field(default_factory=set)

    async def write_if_changed(self, path: pathlib.Path, content: bytes):
        self.seen_files.add(path)
        try:
            async with aiofiles.open(path, "rb") as f:
                existing_content = await f.read()
        except OSError:
            pass
        else:
            if existing_content == content:
                return

        self.changed_files.add(path)
        await aiofiles.os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(content)

    async def remove_unseen(self, base_dir: pathlib.Path):
        unlink_paths: list[pathlib.Path] = []
        for path in base_dir.rglob("*"):
            if path not in self.seen_files and await aiofiles.os.path.isfile(path):
                unlink_paths.append(path)
                self.changed_files.add(path)

        await asyncio.gather(*(aiofiles.os.unlink(x) for x in unlink_paths))

    async def commit(self, message: str) -> None:
        async with commit_lock:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "add",
                *[str(path) for path in self.changed_files],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode != 0:
                raise RuntimeError("git add failed")

            proc = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                message,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode != 0:
                raise RuntimeError("git commit failed")


@dataclasses.dataclass
class Agency:
    id: str
    static_url: str
    realtime_urls: list[str]

    @property
    def agency_dir(self) -> pathlib.Path:
        return HERE / self.id

    @property
    def static_dir(self) -> pathlib.Path:
        return self.agency_dir / "static"

    @property
    def realtime_dir(self) -> pathlib.Path:
        return self.agency_dir / "realtime"

    @property
    def vehicles_dir(self) -> pathlib.Path:
        return self.realtime_dir / "vehicles"

    @property
    def alerts_dir(self) -> pathlib.Path:
        return self.realtime_dir / "alerts"

    async def update_static(
        self,
        session: aiohttp.ClientSession,
        commit: bool = True,
        warn_http_errors: bool = False,
    ) -> None:
        try:
            async with session.get(self.static_url) as response:
                response.raise_for_status()
                zip_content = await response.read()
        except aiohttp.ClientError as e:
            gha.warning(f"Failed to fetch static GTFS for {self.id}: {e}")
            if not warn_http_errors or not self.static_dir.exists():
                raise
            return

        tracker = FileTracker()
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            for file_info in z.infolist():
                file_path = self.static_dir / file_info.filename
                contents = z.read(file_info.filename)
                new_contents = csv_normalize(contents)
                await tracker.write_if_changed(file_path, new_contents)

        await tracker.remove_unseen(self.static_dir)

        if not tracker.changed_files:
            gha.debug(f"{self.id}: No changes to static GTFS data")
            return

        if commit:
            await tracker.commit(f"{self.id}: Update static GTFS data")

    async def update_realtime(
        self,
        session: aiohttp.ClientSession,
        commit: bool = True,
        warn_http_errors: bool = False,
    ) -> None:
        tracker = FileTracker()

        for url in self.realtime_urls:
            try:
                async with session.get(url) as response:
                    response.raise_for_status()
                    pb_content = await response.read()
            except aiohttp.ClientError as e:
                gha.warning(
                    f"Failed to fetch realtime GTFS data for {self.id} ({url}): {e}"
                )
                if not warn_http_errors or not self.realtime_dir.exists():
                    raise
                return

            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(pb_content)
            for entity in feed.entity:
                if entity.HasField("vehicle") and entity.vehicle.vehicle.label:
                    await tracker.write_if_changed(
                        self.vehicles_dir / f"{entity.vehicle.vehicle.label}.txtpb",
                        text_format.MessageToString(entity.vehicle).encode(),
                    )
                if entity.HasField("alert"):
                    await tracker.write_if_changed(
                        self.alerts_dir / f"{entity.id}.txtpb",
                        text_format.MessageToString(entity.alert).encode(),
                    )

        await tracker.remove_unseen(self.realtime_dir)
        if not tracker.changed_files:
            gha.debug(f"{self.id}: No changes to realtime GTFS data")
            return

        if commit:
            await tracker.commit(f"{self.id}: Update realtime GTFS data")


AGENCIES = [
    Agency(
        id="rtd",
        static_url="https://www.rtd-denver.com/files/gtfs/google_transit.zip",
        realtime_urls=[
            f"https://www.rtd-denver.com/files/gtfs-rt/{x}.pb"
            for x in ("VehiclePosition", "Alerts")
        ],
    ),
    Agency(
        id="via",
        static_url="https://passio3.com/viaboulder/passioTransit/gtfs/google_transit.zip",
        realtime_urls=[
            f"https://passio3.com/viaboulder/passioTransit/gtfs/realtime/{x}"
            for x in ("vehiclePositions", "serviceAlerts")
        ],
    ),
]


@app.async_command()
async def main(
    agencies: Annotated[Optional[list[str]], typer.Argument()] = None,
    *,
    commit: bool = False,
    warn_http_errors: bool = False,
):
    if agencies:
        agencies_to_update = [agency for agency in AGENCIES if agency.id in agencies]
    else:
        agencies_to_update = AGENCIES

    awaitables = []
    async with aiohttp.ClientSession() as session:
        for agency in agencies_to_update:
            awaitables.append(
                agency.update_static(
                    session, commit=commit, warn_http_errors=warn_http_errors
                )
            )
            awaitables.append(
                agency.update_realtime(
                    session, commit=commit, warn_http_errors=warn_http_errors
                )
            )

        await asyncio.gather(*awaitables)


if __name__ == "__main__":
    app()
