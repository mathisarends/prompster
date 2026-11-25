/** Lets keyed elements glide to their new place when a re-render moves them (FLIP). */
export class Flip {
  private tops = new Map<string, number>();
  /** Remembers where the elements are. Call before the DOM changes. */
  capture(elements: Iterable<HTMLElement>): void {
    this.tops.clear();
    for (const element of elements) {
      this.tops.set(element.dataset.key!, element.offsetTop);
    }
  }
  /** Animates every remembered element from its old place to where it is now. */
  play(elements: Iterable<HTMLElement>): void {
    for (const element of elements) {
      const before = this.tops.get(element.dataset.key!);
      if (before !== undefined && before !== element.offsetTop) {
        element.animate(
          [{ transform: `translateY(${before - element.offsetTop}px)` }, { transform: "none" }],
          { duration: 300, easing: "cubic-bezier(0.2, 0.7, 0.2, 1)" },
        );
      }
    }
    this.tops.clear();
  }
}
