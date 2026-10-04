import { css } from "lit";
import { workspaceStyles } from "./workspace";

export const pageStyles = css`
  ${workspaceStyles}
  .muted {
    color: var(--color-muted);
  }
  .error {
    color: var(--color-error);
    background: var(--color-error-surface);
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 13px;
  }
  .status {
    padding: 40px 24px;
    text-align: center;
    color: var(--color-muted);
  }
  .field {
    display: grid;
    gap: 7px;
    margin-bottom: 16px;
    font-size: 12px;
  }
  .input {
    width: 100%;
    border: 1px solid var(--color-border);
    border-radius: 10px;
    padding: 12px;
    background: var(--color-sidebar);
    color: var(--color-text);
  }
  .actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: 20px;
  }
  dialog {
    width: min(500px, calc(100vw - 40px));
    max-height: calc(100dvh - 48px);
    overflow: auto;
    padding: 28px;
    border: 1px solid var(--color-border);
    border-radius: 20px;
    color: var(--color-text);
    background: var(--color-sidebar);
    box-shadow: var(--shadow-panel);
  }
  dialog::backdrop {
    background: #000a;
    backdrop-filter: blur(5px);
  }
  dialog h2 {
    margin: 0 0 12px;
    font-size: 21px;
  }
  dialog p {
    color: var(--color-muted);
    font-size: 13px;
  }
  .tag {
    border: 1px solid var(--color-border);
    border-radius: 20px;
    padding: 4px 9px;
    font-size: 10px;
  }
`;
