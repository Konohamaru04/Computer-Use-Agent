export function normalizeLocalPath(path: string): string {
  return path.replace(/\\/g, "/");
}

export function screenshotAssetUrl(convertedUrl: string, version: number): string {
  const separator = convertedUrl.includes("?") ? "&" : "?";
  return `${convertedUrl}${separator}v=${version}`;
}
