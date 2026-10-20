/** Return url only if it's a safe http(s) link, else undefined. */
export function safeHref(url: string): string | undefined {
  return /^https?:\/\//i.test(url) ? url : undefined;
}
