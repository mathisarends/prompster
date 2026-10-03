import { css } from "lit";
import { controls } from "./controls";
import { scrollbarStyles } from "./scrollbar";

/** Shared controls also used by auth, sized for the denser workspace. */
export const workspaceStyles = css`
  ${controls}
  :host {
    font-family: var(--font-sans);
    font-size: var(--font-size-body);
    line-height: var(--line-height-body);
    font-weight: var(--font-weight-body);
    letter-spacing: var(--letter-spacing-ui);
    color: var(--color-text);
  }
  strong,
  b {
    font-weight: var(--font-weight-emphasis);
  }
  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    font-weight: var(--font-weight-heading);
    letter-spacing: var(--letter-spacing-heading);
  }
  .button {
    min-height: 34px;
    gap: 8px;
    padding: 8px 14px;
    border: 0;
    border-radius: var(--radius-pill);
    font-size: var(--font-size-label);
  }
  .button.primary:hover:not(:disabled) {
    transform: none;
  }
  .icon-button {
    width: 32px;
    height: 32px;
    display: inline-grid;
    place-items: center;
    flex: 0 0 auto;
    padding: 0;
    border: 0;
    border-radius: var(--radius-control);
    background: transparent;
    color: var(--color-muted);
    cursor: pointer;
  }
  .icon-button:hover {
    color: var(--color-text);
    background: var(--color-panel-hover);
  }
  button:focus-visible,
  a:focus-visible,
  input:focus-visible,
  textarea:focus-visible,
  select:focus-visible,
  [tabindex]:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
  }
  input,
  textarea,
  select {
    font-family: var(--font-sans);
    accent-color: var(--color-accent);
  }
  input::placeholder,
  textarea::placeholder {
    color: var(--color-muted);
    opacity: 1;
  }
  input:focus-visible,
  select:focus-visible {
    outline: none;
    box-shadow: 0 0 0 2px var(--color-muted);
  }
  ${scrollbarStyles}
`;
