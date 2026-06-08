// Async loader with timing bug
export class DataLoader {
  private data: string | null = null;

  async load(): Promise<void> {
    // BUG: No proper async handling - data not awaited
    setTimeout(() => {
      this.data = 'loaded content';
    }, 100);
  }

  getData(): string {
    return this.data || '';
  }
}
