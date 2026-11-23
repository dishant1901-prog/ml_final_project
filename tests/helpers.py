"""Synthetic satellite/OSM inputs for exercising the real pipeline offline."""

import json
import asyncio
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.transform import from_origin


async def asgi_request(
    app, method, path, *, body=None, token=None, query=b"", timeout=30, extra_headers=None
):
    """In-process HTTP exchange through the real ASGI middleware, without sockets."""
    payload = json.dumps(body).encode() if body is not None else b""
    headers = [(b"host", b"localhost"), (b"content-type", b"application/json")]
    if token:
        headers.append((b"authorization", ("Bearer " + token).encode()))
    headers.extend(extra_headers or [])
    scope = dict(type="http", asgi={"version": "3.0"}, http_version="1.1",
                 method=method, scheme="http", path=path, raw_path=path.encode(),
                 query_string=query, headers=headers, server=("localhost", 80),
                 client=("127.0.0.1", 1234), root_path="")
    sent = False
    finished = asyncio.Event()
    messages = []

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return dict(type="http.request", body=payload, more_body=False)
        await finished.wait()
        return dict(type="http.disconnect")

    async def send(message):
        messages.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            finished.set()

    await asyncio.wait_for(app(scope, receive, send), timeout=timeout)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    content = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, content


def synthetic_manifest(root: Path, *, optical: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    crs = "EPSG:32645"
    x, y = Transformer.from_crs(4326, crs, always_xy=True).transform(85.35, 28.2)
    transform = from_origin(x, y, 20, 20)
    size = 32
    to_wgs = Transformer.from_crs(crs, 4326, always_xy=True).transform
    west, south = to_wgs(x + 40, y - 600)
    east, north = to_wgs(x + 600, y - 40)

    def raster(name, values):
        path = root / (name + ".tif")
        if values.ndim == 2:
            values = values[None]
        with rasterio.open(path, "w", driver="GTiff", width=size, height=size,
                           count=len(values), dtype="float32", crs=crs,
                           transform=transform, nodata=np.nan) as dst:
            dst.write(values.astype("float32"))
        return path.name

    vv = np.full((size, size), -10.0)
    post = vv.copy()
    post[8:20, 8:20] = -22
    pre_paths = [raster(f"before-{i}", np.stack([vv, vv - 5])) for i in range(3)]
    post_path = raster("after", np.stack([post, post - 5]))
    dem_path = raster("elevation", np.tile(np.linspace(100, 90, size)[:, None], (1, size)))
    common = dict(source="SYNTHETIC TEST ONLY", relative_orbit=85, **{"pass": "ASCENDING"},
                  instrument_mode="IW", polarization="VV/VH", units="dB",
                  native_sensor_resolution_m=10, platform="S1A")
    manifest = dict(
        event_date="2026-08-26", bbox=[west, south, east, north], synthetic=True,
        pre=[dict(common, path=path, timestamp=day + "T12:00:00Z", scene_id="synthetic-pre-" + day)
             for path, day in zip(pre_paths, ("2026-08-01", "2026-08-13", "2026-08-25"))],
        post=dict(common, path=post_path, timestamp="2026-08-28T12:00:00Z", scene_id="synthetic-post"),
        dem=dict(path=dem_path, source="SYNTHETIC TEST ONLY", synthetic=True),
        osm=dict(snapshot="2026-08-25T00:00:00Z", source="SYNTHETIC TEST ONLY"),
    )

    def point(px, py):
        return list(to_wgs(x + px, y - py))

    def feature(identifier, kind, coords, **props):
        return dict(type="Feature", geometry=dict(type=kind, coordinates=coords),
                    properties=dict(id=identifier, edit_timestamp="2026-08-01T00:00:00Z", **props))

    vectors = {
        "roads": [feature("way/1", "LineString", [point(80, 280), point(560, 280)],
                          highway="residential", layer="0", bridge="no")],
        "buildings": [feature("building/1", "Polygon", [[point(200, 200), point(240, 200),
                         point(240, 240), point(200, 240), point(200, 200)]], building="yes")],
        "settlements": [feature("node/1", "Point", point(100, 280), name="Synthetic village", place="village")],
        "destinations": [feature("node/2", "Point", point(540, 280), name="Synthetic town", place="town")],
    }
    for name, rows in vectors.items():
        path = root / (name + ".geojson")
        path.write_text(json.dumps(dict(type="FeatureCollection", features=rows)))
        manifest["osm"][name] = path.name
    if optical:
        bands = np.stack([np.full_like(vv, n) for n in (2000, 1000, 3000, 2000, 4)])
        for name, day in (("optical_pre", "2026-08-20"), ("optical_post", "2026-08-29")):
            path = raster(name, bands)
            manifest[name] = dict(path=path, source="SYNTHETIC OPTICAL", timestamp=day + "T12:00:00Z")
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path
