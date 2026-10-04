import type { FeatureCollection } from "geojson";
import {
  type GeoJSONSource,
  Map as LibreMap,
  Marker,
  NavigationControl,
  setWorkerUrl,
} from "maplibre-gl";
import { useEffect, useRef, useState } from "react";
import type { Hit } from "../api/schema";
import fiji from "../assets/fiji.json";
import { features, mapBounds } from "./model";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";

// Bundle the module worker and its imports locally in both Vite dev and production.
setWorkerUrl(workerUrl);

export function ResultMap({
  hits,
  focus,
  onSelect,
}: {
  hits: readonly Hit[];
  focus: Hit | null;
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<LibreMap | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const select = useRef(onSelect);
  select.current = onSelect;
  useEffect(() => {
    if (!container.current) return;
    let instance: LibreMap;
    const markers: Marker[] = [];
    try {
      instance = new LibreMap({
        container: container.current,
        center: [179, -17.8],
        zoom: 5,
        maxZoom: 14,
        attributionControl: false,
        renderWorldCopies: true,
        // No glyphs, tiles, sprites, remote styles, or geolocation provider.
        style: {
          version: 8,
          sources: {
            land: { type: "geojson", data: fiji as FeatureCollection },
          },
          layers: [
            {
              id: "ocean",
              type: "background",
              paint: { "background-color": "#e6efed" },
            },
            {
              id: "land",
              type: "fill",
              source: "land",
              paint: { "fill-color": "#fcfaf4" },
            },
            {
              id: "coast",
              type: "line",
              source: "land",
              paint: { "line-color": "#91aaa3", "line-width": 1.3 },
            },
          ],
        },
      });
      map.current = instance;
      instance.addControl(
        new NavigationControl({ showCompass: false }),
        "top-right",
      );
      instance
        .getCanvas()
        .setAttribute(
          "aria-label",
          "Approximate result map. Use the result list for all observations.",
        );
      instance.on("error", () => setFailed(true));
      instance.on("load", () => {
        instance.addSource("observations", {
          type: "geojson",
          data: features([]),
          cluster: true,
          clusterRadius: 48,
          clusterMaxZoom: 12,
        });
        instance.addLayer({
          id: "clusters",
          type: "circle",
          source: "observations",
          filter: ["has", "point_count"],
          paint: {
            "circle-radius": 20,
            "circle-color": "#176958",
            "circle-stroke-width": 5,
            "circle-stroke-color": "#b1d4c6",
          },
        });
        instance.addLayer({
          id: "points",
          type: "circle",
          source: "observations",
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-radius": 7,
            "circle-stroke-width": 2,
            "circle-stroke-color": "#ffffff",
            "circle-color": [
              "match",
              ["get", "category"],
              "web_server",
              "#176958",
              "ssh_server",
              "#426a9d",
              "mail_server",
              "#895322",
              "multiple",
              "#795599",
              "unknown",
              "#616e76",
              "#985144",
            ],
          },
        });
        setReady(true);
      });
      let markerSignature = "";
      const update = () => {
        if (
          !instance.getSource("observations") ||
          !instance.isSourceLoaded("observations")
        )
          return;
        const clusters = instance
          .querySourceFeatures("observations")
          .filter((f) => f.properties.point_count);
        const signature = JSON.stringify(
          clusters.map((f) => [
            f.properties.cluster_id,
            f.properties.point_count,
            f.geometry,
          ]),
        );
        if (signature === markerSignature) return;
        markerSignature = signature;
        for (const marker of markers.splice(0)) marker.remove();
        const seen = new Set<number>();
        for (const feature of clusters) {
          const { cluster_id: id, point_count: count } = feature.properties;
          if (!count || seen.has(id) || feature.geometry.type !== "Point")
            continue;
          seen.add(id);
          const coordinates = feature.geometry.coordinates as [number, number];
          const button = document.createElement("button");
          button.className = "cluster-count";
          button.textContent = String(count);
          button.setAttribute(
            "aria-label",
            `Zoom into cluster of ${count} displayed observations`,
          );
          button.onclick = () => {
            const source = instance.getSource("observations") as GeoJSONSource;
            void source
              .getClusterExpansionZoom(id)
              .then((zoom) => {
                if (map.current === instance)
                  instance.easeTo({ center: coordinates, zoom, duration: 0 });
              })
              .catch(() => {});
          };
          markers.push(
            new Marker({ element: button })
              .setLngLat(coordinates)
              .addTo(instance),
          );
        }
      };
      instance.on("idle", update);
      instance.on("click", "points", (event) => {
        const id = event.features?.[0]?.properties.id;
        if (typeof id === "string") select.current(id);
      });
    } catch {
      setFailed(true);
    }
    return () => {
      map.current = null;
      for (const marker of markers) marker.remove();
      instance?.remove();
    };
  }, []);
  useEffect(() => {
    if (!ready || !map.current) return;
    const data = features(hits);
    (map.current.getSource("observations") as GeoJSONSource).setData(data);
    const bounds = mapBounds(data.features.map((f) => f.geometry.coordinates));
    if (bounds)
      map.current.fitBounds(bounds, { padding: 65, maxZoom: 7, duration: 0 });
  }, [hits, ready]);
  useEffect(() => {
    if (focus?.place?.point && ready)
      map.current?.easeTo({
        center: [...focus.place.point],
        zoom: 10,
        duration: 0,
      });
  }, [focus, ready]);
  return (
    <section className="map-panel" aria-label="Geographic map">
      <div ref={container} className="map-canvas" />
      {failed && (
        <p className="map-error" role="status">
          Map rendering is unavailable. All results remain accessible in the
          list.
        </p>
      )}
      <div className="map-label">
        <strong>FIJI / OFFLINE BASEMAP</strong>
        <span>Generalized land only · no global basemap coverage</span>
      </div>
      <p className="map-credit">
        Made with Natural Earth v5.1.2 · Public domain · MapLibre
      </p>
    </section>
  );
}
