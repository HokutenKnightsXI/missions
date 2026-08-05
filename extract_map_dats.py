"""Inventory Remapster minimap DATs and optionally extract their PNG artwork.

The DAT decoding follows the documented FFXI 0xB1 ``menumap`` layout. The
source pack and extracted images stay under map-dats/, which is git-ignored.
"""

import argparse
import json
import re
import struct
from pathlib import Path

from PIL import Image

from build_loot_tables import SOURCES, fetch, parse_zones


MAP_ID = re.compile(rb"(?:menumap\s+)?m_(\d{1,3})_(\d{1,2})", re.I)
DAT_HEADER = 8
BLOCK_PADDING = 8


def identify(path):
    with path.open("rb") as handle:
        match = MAP_ID.search(handle.read(65536))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def find_texture(path):
    data = path.read_bytes()
    offset = 0
    while offset + DAT_HEADER <= len(data):
        packed = struct.unpack_from("<I", data, offset + 4)[0]
        block_type = packed & 0x7F
        units = (packed >> 7) & 0x7FFFF
        if not units:
            break
        block_size = units * 16
        if block_type == 0x20:
            start = offset + DAT_HEADER + BLOCK_PADDING
            if start < len(data) and data[start] in (0x81, 0xA1, 0xB1):
                return data, start, offset + block_size
        offset += block_size
    raise ValueError("no supported menumap texture found")


def extract_image(dat_path, output_path, max_size=1200):
    data, start, block_end = find_texture(dat_path)
    width, height = struct.unpack_from("<ii", data, start + 0x15)
    if not (0 < width <= 2048 and 0 < height <= 2048):
        raise ValueError(f"invalid texture dimensions {width}x{height}")
    if data[start] in (0x81, 0xA1):
        dds_type = data[start + 57:start + 61]
        dds_size = struct.unpack_from("<I", data, start + 61)[0]
        pixels_start = start + 69
        pixels_end = pixels_start + dds_size
        if pixels_end > min(block_end, len(data)) or dds_type not in (b"1TXD", b"3TXD"):
            raise ValueError("invalid DXT minimap texture")
        image = Image.frombytes(
            "RGBA", (width, height), data[pixels_start:pixels_end],
            "bcn", 1 if dds_type == b"1TXD" else 2,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        image.save(output_path, "WEBP", quality=82, method=6)
        return image.width, image.height

    palette_start = start + 64
    pixels_start = palette_start + 1024
    pixels_end = pixels_start + width * height
    if pixels_end > min(block_end, len(data)):
        raise ValueError("compressed minimap texture is not yet supported")
    palette = data[palette_start:pixels_start]
    indices = data[pixels_start:pixels_end]
    rgb_palette = []
    alpha_palette = bytearray()
    for offset in range(0, len(palette), 4):
        b, g, r, alpha = palette[offset:offset + 4]
        rgb_palette.extend((r, g, b))
        alpha_palette.append(255 if alpha else 0)
    image = Image.frombytes("P", (width, height), indices)
    image.putpalette(rgb_palette)
    image.info["transparency"] = bytes(alpha_palette)
    image = image.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    image.save(output_path, "WEBP", quality=82, method=6)
    return image.width, image.height


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("map-dats"))
    parser.add_argument("--manifest", type=Path, default=Path("map-dats/map_manifest.json"))
    parser.add_argument("--extract", action="store_true", help="extract matching maps as WebP")
    parser.add_argument("--force", action="store_true", help="replace existing extracted maps")
    parser.add_argument("--zone", type=int, help="limit extraction to one numeric zone ID")
    args = parser.parse_args()

    zones = parse_zones(fetch(SOURCES["zones"]))
    records = []
    for dat_path in sorted(args.source.rglob("*.DAT")):
        identity = identify(dat_path)
        if not identity:
            records.append({"path": str(dat_path.relative_to(args.source)), "error": "missing map ID"})
            continue
        zone_id, map_id = identity
        record = {
            "path": str(dat_path.relative_to(args.source)).replace("\\", "/"),
            "zone_id": zone_id,
            "zone": zones.get(zone_id, "Unknown").replace("_", " "),
            "map_id": map_id,
        }
        if args.extract and (args.zone is None or args.zone == zone_id):
            output = args.source / "extracted" / str(zone_id) / f"map_{map_id:02d}.webp"
            try:
                if output.exists() and not args.force:
                    try:
                        with Image.open(output) as existing:
                            width, height = existing.size
                    except OSError:
                        width, height = extract_image(dat_path, output)
                else:
                    width, height = extract_image(dat_path, output)
                record.update({"image": str(output.relative_to(args.source)).replace("\\", "/"),
                               "width": width, "height": height})
            except ValueError as error:
                record["extract_error"] = str(error)
        records.append(record)

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(records, indent=2), encoding="utf-8")
    extracted = sum("image" in record for record in records)
    print(f"Identified {len(records):,} DATs; extracted {extracted:,}; wrote {args.manifest}")


if __name__ == "__main__":
    main()
