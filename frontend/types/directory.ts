// Provider directory entry for client-side nearby search.
// Matches provider_directory.json schema from pipeline/export/build_json.py.
// Short keys minimize file size (~100 bytes per entry, ~5K hospitals).

export interface DirectoryEntry {
  id: string;         // CCN
  n: string;          // name
  c: string | null;   // city
  s: string | null;   // state (2-char)
  z: string | null;   // zip (5-char)
  t: string;          // provider_type ("HOSPITAL" | "NURSING_HOME")
  lat: number | null;  // latitude (zip centroid for hospitals, CMS-published for NHs)
  lon: number | null;  // longitude
}
