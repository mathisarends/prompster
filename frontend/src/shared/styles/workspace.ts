import { css } from "lit";
import { controls } from "./controls";
import { scrollbarStyles } from "./scrollbar";

/** Base typography plus shared controls for every workspace component. */
export const workspaceStyles = css`
  ${controls}
  :host {
    font-family: var(--font-sans);
    font-size: var(--font-size-body);
    line-height: var(--line-height-body);
    font-weight: var(--font-weight-regular);
    letter-spacing: var(--letter-spacing-ui);
    color: var(--color-text);
  }
  strong,
  b {
    font-weight: var(--font-weight-semibold);
  }
  h1,
  h2,
  h3,
  h4,
  h5,
  h6 {
    font-weight: var(--font-weight-semibold);
    letter-spacing: var(--letter-spacing-heading);
  }
  ${scrollbarStyles}
`;
