import { css } from "lit";

/** Native controls preserve form submission, autofill and browser validation. */
export const controls = css`
  *,
  *::before,
  *::after {
    box-sizing: border-box;
  }
  button,
  input,
  textarea,
  select {
    font: inherit;
    letter-spacing: inherit;
  }
  button,
  a,
  input {
    -webkit-tap-highlight-color: transparent;
  }
  button {
    cursor: pointer;
  }
  button:disabled {
    cursor: default;
    opacity: 0.5;
  }
  input,
  textarea,
  select {
    accent-color: var(--color-text);
  }
  input::placeholder,
  textarea::placeholder {
    color: var(--color-faint);
    opacity: 1;
  }
  :focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 2px;
  }
  a {
    color: var(--color-text);
    text-decoration-color: var(--color-faint);
    text-underline-offset: 3px;
  }
  a:hover {
    text-decoration-color: currentColor;
  }

  /* Buttons: outlined by default, white for the primary action. */
  .button {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid var(--color-border-strong);
    border-radius: var(--radius-pill);
    background: transparent;
    color: var(--color-text);
    font-size: var(--font-size-label);
    font-weight: var(--font-weight-medium);
    text-decoration: none;
    white-space: nowrap;
    vertical-align: middle;
    transition:
      background 0.15s,
      border-color 0.15s;
  }
  .button:hover:not(:disabled) {
    border-color: var(--color-faint);
    background: var(--color-hover);
  }
  .button.primary {
    border-color: var(--color-text);
    background: var(--color-text);
    color: var(--color-inverse);
  }
  .button.primary:hover:not(:disabled) {
    border-color: var(--color-text-strong);
    background: var(--color-text-strong);
  }
  .button.danger {
    border-color: color-mix(in srgb, var(--color-error) 40%, transparent);
    color: var(--color-error);
  }
  .button.danger:hover:not(:disabled) {
    border-color: var(--color-error);
    background: var(--color-error-surface);
  }
  .icon-button {
    display: inline-grid;
    place-items: center;
    flex: 0 0 auto;
    width: 32px;
    height: 32px;
    padding: 0;
    border: 0;
    border-radius: var(--radius-control);
    background: transparent;
    color: var(--color-muted);
    transition:
      background 0.15s,
      color 0.15s;
  }
  .icon-button:hover:not(:disabled) {
    color: var(--color-text);
    background: var(--color-chip);
  }
  .text-button {
    padding: 2px 0;
    border: 0;
    background: none;
    color: var(--color-text);
    font-size: inherit;
    text-decoration: underline;
    text-decoration-color: var(--color-faint);
    text-underline-offset: 3px;
  }
  .text-button:hover {
    text-decoration-color: currentColor;
  }

  /* Text fields and selects. */
  .input {
    width: 100%;
    min-height: 36px;
    padding: 8px 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-control);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: var(--font-size-body);
    transition: border-color 0.15s;
  }
  .input:hover {
    border-color: var(--color-border-strong);
  }
  .input:focus-visible {
    outline: none;
    border-color: var(--color-faint);
  }

  .eyebrow {
    margin: 0;
    color: var(--color-faint);
    font-family: var(--font-mono);
    font-size: var(--font-size-micro);
    letter-spacing: var(--letter-spacing-eyebrow);
    text-transform: uppercase;
  }
  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation: none !important;
      transition: none !important;
    }
  }
`;
