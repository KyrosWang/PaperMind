import type { NextRequest } from "next/server";

const backend = process.env.API_URL ?? "http://localhost:8000/api";

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const target = new URL(`${backend}/${path.join("/")}`);
  target.search = request.nextUrl.search;
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  headers.set("X-API-Key", process.env.APP_API_KEY ?? "change-me");
  const response = await fetch(target, {
    method: request.method,
    headers,
    body: request.method === "GET" ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  });
  const responseHeaders = new Headers();
  for (const name of ["content-type", "content-length", "content-disposition"]) {
    const value = response.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }
  return new Response(response.body, { status: response.status, headers: responseHeaders });
}

export const GET = forward;
export const POST = forward;

