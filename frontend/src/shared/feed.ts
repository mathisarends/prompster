/** A synchronous broadcast: every listener sees each value as it is published. */
export class Feed<T> {
  private listeners = new Set<(value: T) => void>();
  publish(value: T): void {
    for (const listener of this.listeners) {
      listener(value);
    }
  }
  /** Returns the function that ends the subscription. */
  subscribe(listener: (value: T) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}
