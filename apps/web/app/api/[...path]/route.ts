const BACKEND = process.env.QUANT_API_URL ?? "http://localhost:8000";

async function proxy(req: Request, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const search = new URL(req.url).search;
  const url = `${BACKEND}/api/${path.join("/")}${search}`;
  const init: RequestInit = {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") init.body = await req.text();
  try {
    const res = await fetch(url, init);
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ error: "quant-api 不可达，请先启动 dev:api" }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST };
