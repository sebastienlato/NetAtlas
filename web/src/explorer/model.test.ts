import { expect, it } from "vitest";
import { hit, places } from "./fixtures";
import { features, mapBounds, placeFilter } from "./model";

it("maps only known valid points; dateline bounds do not span the world", () => {
  expect(
    features([
      hit,
      { ...hit, geography_state: "stale" },
      { ...hit, place: null },
    ]).features,
  ).toHaveLength(1);
  expect(
    mapBounds([
      [179.5, -17.5],
      [-179.5, -17.5],
    ]),
  ).toEqual([
    [179.5, -17.5],
    [180.5, -17.5],
  ]);
});
it("keeps place identity, country association and boundary predicates distinct", () => {
  expect(placeFilter(places.places[0])).toEqual({ place_id: "fixture:east" });
  expect(placeFilter({ ...places.places[0], kind: "country" })).toEqual({
    country: "FJ",
  });
  expect(placeFilter({ ...places.places[0], kind: "region" }, true)).toEqual({
    boundary_place_id: "fixture:east",
  });
});
