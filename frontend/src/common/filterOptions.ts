type FilterState = Record<string, boolean>;

const withActive = (
  definitions: { key: string; label: string }[],
  filters: FilterState | string,
) => definitions.map((opt) => ({
  ...opt,
  active: typeof filters === "string" ? filters === opt.key : !!filters[opt.key],
}));

export const positionOptions = (filters: FilterState | string) =>
  withActive([
    { key: "ip", label: "IP" },
    { key: "oop", label: "OOP" },
  ], filters);

export const boardTypeOptions = (filters: FilterState | string) =>
  withActive([
    { key: "monotone", label: "MONOTONE" },
    { key: "twoTone", label: "2TONE" },
    { key: "rainbow", label: "RAINBOW" },
  ], filters);

export const potTypeOptions = (filters: FilterState | string) =>
  withActive([
    { key: "srp", label: "SRP" },
    { key: "threeBet", label: "3BET" },
    { key: "fourBet", label: "4BET" },
  ], filters);

export const turnRunoutOptions = (filters: FilterState | string) =>
  withActive([
    { key: "overcard", label: "OVERCARD" },
    { key: "flushCompleting", label: "FLUSH" },
    { key: "paired", label: "PAIRED" },
    { key: "other", label: "OTHER" },
  ], filters);

export const actionLineOptions = (filters: FilterState | string) =>
  withActive([
    { key: "xx", label: "XX" },
    { key: "xbc", label: "XBC" },
    { key: "xbrc", label: "XBRC" },
    { key: "bc", label: "BC" },
  ], filters);

export const flopRankTextureOptions = (filters: FilterState | string) =>
  withActive([
    { key: "trips", label: "TRIPS" },
    { key: "paired", label: "PAIRED" },
    { key: "unpaired", label: "UNPAIRED" },
  ], filters);
