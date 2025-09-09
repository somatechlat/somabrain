export type RecallResponse = {
  wm: Array<{ score: number; payload: Record<string, any> }>;
  memory: Array<Record<string, any>>;
  namespace: string;
  trace_id: string;
};

export class SomaBrainClient {
  private base: string;
  private headers: Record<string, string>;

  constructor(baseUrl: string, opts?: { token?: string; tenant?: string }) {
    this.base = baseUrl.replace(/\/$/, "");
    this.headers = { "Content-Type": "application/json" };
    if (opts?.token) this.headers["Authorization"] = `Bearer ${opts.token}`;
    if (opts?.tenant) this.headers["X-Tenant-ID"] = String(opts.tenant);
  }

  async remember(payload: Record<string, any>, coord?: string): Promise<any> {
    const body = { coord: coord ?? null, payload };
    const res = await fetch(`${this.base}/remember`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`remember failed: ${res.status}`);
    return await res.json();
  }

  async recall(query: string, top_k = 3, universe?: string): Promise<RecallResponse> {
    const body: any = { query, top_k };
    if (universe) body.universe = universe;
    const res = await fetch(`${this.base}/recall`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`recall failed: ${res.status}`);
    return (await res.json()) as RecallResponse;
  }

  async link(opts: {
    from_key?: string;
    to_key?: string;
    from_coord?: string;
    to_coord?: string;
    type?: string;
    weight?: number;
    universe?: string;
  }): Promise<any> {
    const res = await fetch(`${this.base}/link`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(opts),
    });
    if (!res.ok) throw new Error(`link failed: ${res.status}`);
    return await res.json();
  }

  async planSuggest(task_key: string, opts?: { max_steps?: number; rel_types?: string[]; universe?: string }): Promise<any> {
    const body: any = { task_key };
    if (opts?.max_steps !== undefined) body.max_steps = opts.max_steps;
    if (opts?.rel_types) body.rel_types = opts.rel_types;
    if (opts?.universe) body.universe = opts.universe;
    const res = await fetch(`${this.base}/plan/suggest`, {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`plan/suggest failed: ${res.status}`);
    return await res.json();
  }
}
