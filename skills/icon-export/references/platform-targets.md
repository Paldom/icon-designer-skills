# Platform icon target matrix

Verified export targets with sources (accessed 2026-07). Tags: [primary]
vendor/spec docs, [community] measured consensus.

**Contents:** Favicons & PWA · Apple · Android/Play · GitHub · ICO format ·
Rounded vs square rule

## Favicons & PWA (the modern minimal set) [primary/community]

Per Evil Martians' maintained "How to Favicon" guidance
(<https://evilmartians.com/chronicles/how-to-favicon-in-2021-six-files-that-fit-most-needs>,
2026 edition: "three files that fit most needs" + PWA extras):

| File | Size | Notes |
| --- | --- | --- |
| `favicon.ico` | 32 (we embed 16+32+48) | legacy default; browsers pick |
| `icon.svg` | vector | `<link rel="icon" type="image/svg+xml">` |
| `apple-touch-icon.png` | 180×180 | iOS home-screen; opaque, full-square (iOS rounds it) |
| `icon-192.png` / `icon-512.png` | 192, 512 | web manifest icons |
| `icon-mask-512.png` | 512, `purpose: maskable` | safe zone below |

Maskable safe zone: the guaranteed-visible region is a centered circle with
radius = **40% of the icon's minimum dimension** (diameter 80%); outer 10%
ring is routinely cropped (web.dev, <https://web.dev/articles/maskable-icon>;
W3C manifest spec). [primary]

Head tags (what `snippet.html` contains):

```html
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
```

## Apple [primary]

- **App Store / Xcode**: one full-square **1024×1024** master; the system
  applies the mask (corner radius ≈ 22.37% of side — community-measured, not
  officially published). Submit square, never pre-rounded
  (<https://developer.apple.com/documentation/Xcode/creating-your-app-icon-using-icon-composer>).
- App Store artwork must be opaque/flattened; if an upload rejects the alpha
  channel: `magick appstore-1024.png -background "#2A2A2E" -alpha remove appstore-flat.png`.
- **macOS .icns** via `iconutil -c icns <name>.iconset`; the `.iconset` folder
  must contain exactly the iconutil-named files
  `icon_16x16.png, icon_16x16@2x.png, icon_32x32.png, icon_32x32@2x.png,
  icon_128x128.png, icon_128x128@2x.png, icon_256x256.png, icon_256x256@2x.png,
  icon_512x512.png, icon_512x512@2x.png` (@2x = double pixels). macOS app
  icons ship *with* their rounded-rect shape baked in (the OS does not mask
  .icns), so the rounded master is the right source.
- iOS/macOS 26 "Liquid Glass": layered icons + 6 appearance variants are
  authored in **Icon Composer** from flat art
  (<https://developer.apple.com/icon-composer/>); the flat 1024 remains the
  valid baseline/fallback. Version-sensitive — re-check at each OS cycle.

## Android / Play Store [primary]

- **Play Store listing icon: 512×512 32-bit PNG, no transparency** (rejected
  otherwise).
- **Adaptive launcher icons** are a two-layer (foreground/background) 108dp
  resource with a **66dp-diameter safe circle** — an app-project artifact
  (Android Studio/resource pipeline), out of scope for a web/OSS export; the
  maskable web icon covers the same visual contract for PWAs.

## GitHub [primary]

- Repo **social preview: 1280×640** recommended (minimum 640×320)
  (<https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview>).
  Uploaded in repo Settings → Social preview (no API for it).
- Org/user avatars: square upload, any reasonable size ≥ 500 px works; we ship
  512 from the **full-square variant** because GitHub applies its own
  (rounded/circular) mask to avatars.

## ICO format [primary]

ICO is a tiny container: `ICONDIR` (6 bytes) + 16-byte `ICONDIRENTRY` per
image + image blobs. Entries may be **PNG-compressed** (supported since
Windows Vista) — that's what the exporter writes, at 16/32/48 px, the sizes
Windows actually picks for tabs/taskbar/desktop
(<https://en.wikipedia.org/wiki/ICO_(file_format)>).

## The rounded-vs-square rule (why two variants exist)

| Surface | Variant | Why |
| --- | --- | --- |
| favicon.ico, icon.svg, 192/512, README/docs, avatars, icns | **rounded master** | nothing else will round it |
| apple-touch-icon, App Store 1024, Play 512, maskable | **square (rx=0)** | platform applies its own mask; pre-rounding double-masks and leaves transparent corner slivers |
