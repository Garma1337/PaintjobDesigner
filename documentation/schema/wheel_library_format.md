[<- Back](../README.md)

# Wheel Library Format

This document describes the on-disk format the designer writes when you "Export Wheel Library As…". A *wheel* replaces the game's tire sprite: the 17 frames the game picks from by viewing angle, each with its own 16-color CLUT and optional 32x32 4bpp pixels.

**Machine-readable schema**: [`schema/wheels_library_schema.json`](../../schema/wheels_library_schema.json). Generated from the pydantic models and kept in lockstep with them via `tests/wheel/test_reader.py`. If the schema and this document ever disagree, the schema wins.

## How the game draws wheels

Each kart draws four camera-facing 32x32 sprites from one shared icon group (`tireAnim` in `shared.mpk`). The frame is chosen per wheel from the angle between the view and the axle: `frame00` is the tread seen edge-on, `frame16` the full side face, the frames in between turn the wheel. Seen from the other side, the sprite is mirrored. There is no rolling animation; frames only change with the viewing angle.

| Frames              | Texpage | VRAM halfword origin (x, y) |
|---------------------|---------|-----------------------------|
| `frame00`–`frame07` | 7       | (448 + 8·n, 216)            |
| `frame08`–`frame15` | 6       | (384 + 8·(n − 8), 216)      |
| `frame16`           | 5       | (320, 216)                  |

Ghosts draw the same pixels through a second set of CLUTs (`trtireAnim`) that are the normal colors with the semi-transparency bit set; a consumer can derive them, so a wheel file only carries the normal CLUTs.

Every racer samples the same icons, so a game can only show one wheel design at a time.

## Directory layout

```
MyWheelLibrary/
├── 00_whitewalls.json
├── 01_gold_rims.json
├── …
```

Files are named `NN_<slug>.json`, `NN` being the library index. Consumers decide what the index means (Saphi reserves id 0 for the game's own tires).

## One wheel file

```json
{
  "schema_version": 1,
  "name": "Whitewalls",
  "author": "Garma",
  "slots": {
    "frame16": {
      "colors": ["#0000", "#8000", "#7fff", "..."],
      "pixels": [
        { "vram_x": 320, "vram_y": 216, "width": 32, "height": 32, "data": "<base64, 512 bytes>" }
      ]
    }
  }
}
```

| Field            | Type   | Meaning                                                                                          |
|------------------|--------|--------------------------------------------------------------------------------------------------|
| `schema_version` | int    | Always `1` currently. Consumers should reject newer versions.                                    |
| `name`           | string | Display name. May be empty.                                                                      |
| `author`         | string | Author tag. May be empty.                                                                        |
| `slots`          | object | Map of `frame00`..`frame16` → frame payload. A missing frame keeps the game's colors and pixels. |

A frame payload is the same shape as a paintjob slot: `colors` (16 PSX colors, `#xxxx`, index 0 transparent, `0x8000` set = semi-transparent texel) and optional `pixels` with exactly one 32x32 4bpp region at the frame's VRAM origin. A frame with colors but no pixels recolors the game's tire.

## Sprite sheets

The designer can export a wheel as one 544x32 PNG (frames left to right) and import any image made of 32x32 cells read left to right, top to bottom, with at least 17 cells. Each frame is quantized to its own 15 colors + transparent on import.
