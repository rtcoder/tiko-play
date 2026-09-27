export const platformNames: Record<string, string> = {
  tiktok: "TikTok",
  twitch: "Twitch",
  youtube: "YouTube",
  kick: "Kick",
};
export function sourceLabel(platform: string, channel: string) {
  return `${platformNames[platform] ?? platform} · ${platform === "youtube" ? "" : "@"}${channel}`;
}
