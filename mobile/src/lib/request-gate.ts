/** Per-screen lock; invalidation prevents late results from a previous input. */
export class RequestGate {
  private generation = 0;
  private active: number | null = null;

  begin(): number | null {
    if (this.active !== null) return null;
    this.active = ++this.generation;
    return this.active;
  }

  isCurrent(ticket: number): boolean { return this.active === ticket; }

  finish(ticket: number): boolean {
    if (!this.isCurrent(ticket)) return false;
    this.active = null;
    return true;
  }

  invalidate(): void { this.active = null; }
}
