/** Invalidates older asynchronous requests when authentication or poll state changes. */
export class RequestEpoch {
  private generation = 0;

  begin(): number {
    this.generation += 1;
    return this.generation;
  }

  snapshot(): number {
    return this.generation;
  }

  invalidate(): void {
    this.generation += 1;
  }

  accepts(generation: number): boolean {
    return generation === this.generation;
  }
}
