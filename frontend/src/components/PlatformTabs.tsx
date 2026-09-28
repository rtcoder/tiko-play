import { t } from "../i18n";
import { useRef } from "react";
import type { Platform } from "../api/types";

const platforms: { id: Platform; label: string; path: string }[] = [
  {
    id: "tiktok",
    label: "TikTok",
    path: "M16.7 1h-4v14.7a3.3 3.3 0 1 1-2.8-3.3V8.3a7.4 7.4 0 1 0 6.8 7.4V8.2a9.6 9.6 0 0 0 5.6 1.8V6a5.7 5.7 0 0 1-5.6-5Z",
  },
  {
    id: "twitch",
    label: "Twitch",
    path: "M3 1 1 5v16h6v3l4-3h5l7-7V1H3Zm18 12-4 4h-5l-4 3v-3H4V3h17v10ZM17 6h-2v6h2V6Zm-6 0H9v6h2V6Z",
  },
  {
    id: "youtube",
    label: "YouTube",
    path: "M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.6 15.6V8.4L15.8 12l-6.2 3.6Z",
  },
  {
    id: "kick",
    label: "Kick",
    path: "M2 2h6v7h3V6h3V2h8v7h-3v3h-3v3h3v3h3v4h-8v-4h-3v-3H8v7H2V2Z",
  },
];

export function PlatformTabs({
  value,
  onChange,
  id,
}: {
  value: Platform;
  onChange: (platform: Platform) => void;
  id: string;
}) {
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);
  return (
    <div
      className="platform-tabs"
      role="tablist"
      aria-label={t("Źródło czatu")}
    >
      {platforms.map((platform, index) => (
        <button
          key={platform.id}
          ref={(element) => {
            buttons.current[index] = element;
          }}
          type="button"
          role="tab"
          id={`${id}-${platform.id}`}
          aria-controls={`${id}-panel`}
          aria-selected={value === platform.id}
          tabIndex={value === platform.id ? 0 : -1}
          className={`platform-tab platform-tab--${platform.id}`}
          onClick={() => onChange(platform.id)}
          onKeyDown={(event) => {
            let next: number;
            switch (event.key) {
              case "ArrowRight":
                next = (index + 1) % platforms.length;
                break;
              case "ArrowLeft":
                next = (index + platforms.length - 1) % platforms.length;
                break;
              case "Home":
                next = 0;
                break;
              case "End":
                next = platforms.length - 1;
                break;
              default:
                return;
            }
            event.preventDefault();
            onChange(platforms[next].id);
            buttons.current[next]?.focus();
          }}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path fill="currentColor" fillRule="evenodd" d={platform.path} />
          </svg>
          <span>{platform.label}</span>
        </button>
      ))}
    </div>
  );
}
