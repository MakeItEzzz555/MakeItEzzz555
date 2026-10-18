# Profile technology icon assets

These SVG icons are vendored into this profile to avoid fragile external
CDN paths and GitHub image-proxy failures. All icons are solid **#7DFFB4**
and are referenced by relative links from the profile README.

- Most icons: [Simple Icons](https://simpleicons.org/) SVGs (CC0-1.0),
  retrieved from the public Simple Icons CDN on 2026-10-18.
- `csharp.svg`, `css3.svg`, `visualstudiocode.svg`, and `windows11.svg`:
  [Devicon](https://github.com/devicons/devicon) plain/original shapes,
  recolored to #7DFFB4 (MIT). Retrieved from public jsDelivr assets
  on 2026-10-18.
- All brand names and marks remain the property of their respective owners.
  This profile is not endorsed by those organizations.
- Eight optional SMIL motion derivatives are generated locally from these
  static logos using `scripts/build_animated_icons.py` (no external scripts).
  Static source logos remain unchanged.
- README `<picture>` markup selects static originals for browsers requesting
  `prefers-reduced-motion: reduce`. All logos retain their original geometry
  and accent color. Animation never depends on a CDN or runtime JavaScript.
- Most technology icons remain static to avoid overwhelming visual motion.
