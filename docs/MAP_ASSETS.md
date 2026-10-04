# Reviewed offline map and demo assets

Two deliberately reviewed, small assets are the Phase 8 exception to the general
rule against committing downloaded datasets/generated outputs. No upstream global
file, observations, raw captures, credentials or generated browser artifacts are
committed. All coordinates come from the already checksum-pinned Phase 5 inputs.

| Committed asset | Contents / transformations | SHA-256 |
| --- | --- | --- |
| `web/src/assets/fiji.json` | Natural Earth 110m country NE_ID 1159320625, geometry only in a FeatureCollection; all properties/other countries omitted. Pretty-printed by Biome. | `4212e3424a74d8318ef213d452072a29aca71675215db8a322ca75aa5f4350ba` |
| `src/netatlas/demo_geography.json` | Canonical output of the existing Phase 5 `build_demo`, plus one newline: Suva/Fiji and fictional documentation-IP/ASN associations with origin notices. Runtime seed adds authored region/same-name places and a fresh explicit demo validity window. | `c40268c934dd123f1afd73e8cbb1ad27cc8326200e1f37b200fcd926581dba47` |

Upstream release: **Natural Earth v5.1.2**. Reviewed source inputs:

- [Populated places simple](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_populated_places_simple.geojson), SHA-256 `0dbd25c9ad8bd797ddf164b067f563be5c16be2c002254eb594862377963f9dc`.
  Suva stable ID `ne:1159150917`; no other place or population data retained.
- [Countries](https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/ne_110m_admin_0_countries.geojson), SHA-256 `6866c877d39cba9c357620878839b336d569f8c662d3cfab4cb1dbe2d39c977f`.
  Fiji stable ID `ne:1159320625`; split antimeridian MultiPolygon unchanged.

[Terms of use](https://www.naturalearthdata.com/about/terms-of-use/) state that the
raster/vector data is public domain. Voluntary visible credit: **Made with Natural
Earth v5.1.2 · Public domain**. Contributors: Natural Earth / NACIS. These generalized
1:110m shapes are not survey/legal boundaries and imply no verified country
membership or location precision. The source URLs are documentation/provenance,
not browser resources. DB-IP Lite, GeoNames and OSM tiles are not bundled or fetched.

The browser never fetches upstream files. Reproduction from the independently
acquired pinned source files uses `netatlas.enrichment.demo.build_demo` for the
packaged fixture, or selects the country feature by NE_ID and removes properties
for the UI outline. A test checks equality of the map geometry and packaged country
boundary. Dataset canonical hashes are separate from file hashes. Runtime fictional
mapping-origin hashes cover extra authored places, ASN rows and city rows in order,
joined by newlines, as documented by that origin. These mappings are not assertions
from Natural Earth. Authored fixture portions remain under repository terms; no
project redistribution license or publication permission is granted by third-party
asset licensing.

MapLibre GL JS **6.12.0** is BSD-3-Clause, with upstream incorporated notices in
`web/public/maplibre-LICENSE.txt`, copied verbatim from its locked package. The build
includes that file and the UI links to it locally. Dependencies, Playwright and Axe
are locked in package-lock; no external map/font service is used. Technical references:
[MapLibre GeoJSON clustering](https://maplibre.org/maplibre-gl-js/docs/examples/cluster/)
and [local worker URL](https://maplibre.org/maplibre-gl-js/docs/API/functions/setWorkerUrl/).
