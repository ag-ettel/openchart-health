// Geographic utility functions for provider proximity search.
// Coordinates are approximate: hospitals use zip code centroids,
// not exact street addresses.

import type { DirectoryEntry } from "@/types/directory";

const EARTH_RADIUS_MILES = 3958.8;

/** Convert degrees to radians. */
function toRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

/**
 * Haversine distance between two points in miles.
 * Returns approximate straight-line distance.
 */
export function haversineDistanceMiles(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return EARTH_RADIUS_MILES * c;
}

export interface DirectoryEntryWithDistance extends DirectoryEntry {
  distanceMiles: number;
}

/**
 * Sort directory entries by Haversine distance from an origin point.
 * Filters out entries with null coordinates.
 */
export function sortByDistance(
  entries: DirectoryEntry[],
  originLat: number,
  originLon: number,
): DirectoryEntryWithDistance[] {
  return entries
    .filter((e): e is DirectoryEntry & { lat: number; lon: number } =>
      e.lat !== null && e.lon !== null,
    )
    .map((e) => ({
      ...e,
      distanceMiles: haversineDistanceMiles(originLat, originLon, e.lat, e.lon),
    }))
    .sort((a, b) => a.distanceMiles - b.distanceMiles);
}
