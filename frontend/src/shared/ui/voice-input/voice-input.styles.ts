import { css } from "lit";
import { workspaceStyles } from "@shared/styles/workspace";

export const voiceInputStyles = css`
  ${workspaceStyles}
  :host {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    min-width: 0;
  }
  .controls {
    flex: none;
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
  }
  .icon-button {
    width: 36px;
    height: 36px;
    color: var(--color-muted);
  }
  .icon-button svg {
    stroke-width: 1.8;
  }
  .capture .icon-button {
    background: var(--color-panel-hover);
    color: var(--color-text);
  }
  .capture .accept {
    color: var(--color-accent);
  }
  .status {
    white-space: nowrap;
    color: var(--color-muted);
    font-size: 12px;
  }
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    border: 0;
  }
  .error {
    margin: 0;
    color: var(--color-error);
    font-size: var(--font-size-caption);
  }
  .wave {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 28px;
    padding-inline: 10px;
    color: var(--color-accent);
  }
  .wave span {
    width: 2px;
    height: 5px;
    border-radius: 2px;
    background: currentColor;
  }
  .wave.listening span {
    animation: pulse 0.85s ease-in-out infinite alternate;
  }
  .wave span:nth-child(3n) {
    animation-delay: -0.35s;
  }
  .wave span:nth-child(3n + 1) {
    animation-delay: -0.6s;
  }
  @keyframes pulse {
    to {
      transform: scaleY(4);
    }
  }
  @media (max-width: 420px) {
    .status {
      font-size: 11px;
    }
    .wave {
      gap: 3px;
      padding-inline: 4px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .wave.listening span {
      animation: none;
    }
  }
`;
