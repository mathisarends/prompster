import { css } from "lit";
import { workspaceStyles } from "./workspace";

/** Page-level building blocks: status text, form fields, alerts and dialogs. */
export const pageStyles = css`
  ${workspaceStyles}
  .muted {
    color: var(--color-muted);
  }
  .error {
    margin: 0 0 12px;
    padding: 10px 14px;
    border-radius: var(--radius-control);
    background: var(--color-error-surface);
    color: var(--color-error);
    font-size: var(--font-size-label);
  }
  .status {
    display: grid;
    justify-items: center;
    gap: 6px;
    padding: 48px 24px;
    color: var(--color-muted);
    text-align: center;
  }
  .status p {
    margin: 0;
  }
  .field {
    display: grid;
    gap: 6px;
    margin-bottom: 16px;
    color: var(--color-muted);
    font-size: var(--font-size-label);
  }
  .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 20px;
  }
  dialog {
    width: min(440px, calc(100vw - 32px));
    max-height: calc(100dvh - 48px);
    overflow: auto;
    padding: 24px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-panel);
    background: var(--color-surface);
    color: var(--color-text);
    box-shadow: var(--shadow-panel);
  }
  dialog::backdrop {
    background: var(--color-backdrop);
    backdrop-filter: blur(4px);
  }
  dialog h2 {
    margin: 0 0 8px;
    font-size: var(--font-size-track);
  }
  dialog p {
    margin: 0 0 8px;
    color: var(--color-muted);
    font-size: var(--font-size-label);
  }
`;
