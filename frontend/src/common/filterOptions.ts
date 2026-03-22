type FilterState = Record<string, boolean>;

const withActive = (
  definitions: { key: string; label: string }[],
  filters: FilterState | string,
) =>
  definitions.map((opt) => ({
    ...opt,
    active:
      typeof filters === "string" ? filters === opt.key : !!filters[opt.key],
  }));

export const positionOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "ip", label: "IP" },
      { key: "oop", label: "OOP" },
    ],
    filters,
  );

export const roleOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "pfr", label: "PFR" },
      { key: "def", label: "DEF" },
    ],
    filters,
  );

export const boardTypeOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "monotone", label: "MONOTONE" },
      { key: "twoTone", label: "2TONE" },
      { key: "rainbow", label: "RAINBOW" },
    ],
    filters,
  );

export const potTypeOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "SRP", label: "SRP" },
      { key: "THREE_BET", label: "3BET" },
      { key: "FOUR_BET", label: "4BET" },
    ],
    filters,
  );

export const turnRunoutOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "OVERCARD", label: "OVERCARD" },
      { key: "FLUSH_COMPLETING", label: "FLUSH" },
      { key: "PAIRED", label: "PAIRED" },
      { key: "OTHER", label: "OTHER" },
    ],
    filters,
  );

export const riverRunoutOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "OVERCARD", label: "OVERCARD" },
      { key: "FLUSH_COMPLETING", label: "FLUSH" },
      { key: "PAIRED", label: "PAIRED" },
      { key: "OTHER", label: "OTHER" },
    ],
    filters,
  );

export const actionLineOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "xx", label: "XX" },
      { key: "xbc", label: "XBC" },
      { key: "xbrc", label: "XBRC" },
      { key: "bc", label: "BC" },
    ],
    filters,
  );

export const flopRankTextureOptions = (filters: FilterState | string) =>
  withActive(
    [
      { key: "trips", label: "TRIPS" },
      { key: "paired", label: "PAIRED" },
      { key: "unpaired", label: "UNPAIRED" },
    ],
    filters,
  );
