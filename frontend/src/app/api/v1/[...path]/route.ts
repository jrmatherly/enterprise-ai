/**
 * API Proxy Route
 *
 * Forwards all /api/v1/* requests to the backend, including cookies.
 * This is needed because Next.js rewrites don't automatically forward cookies.
 */

import { type NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function proxyRequest(request: NextRequest, path: string[]) {
  const url = new URL(`/api/v1/${path.join("/")}`, BACKEND_URL);

  // Forward query params
  request.nextUrl.searchParams.forEach((value, key) => {
    url.searchParams.set(key, value);
  });

  // Build headers, forwarding cookies
  const headers = new Headers();

  // Forward the cookie header (includes better-auth session)
  const cookie = request.headers.get("cookie");
  if (cookie) {
    headers.set("cookie", cookie);
  }

  // Forward Content-Type (important for multipart/form-data)
  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }

  // Forward other relevant headers
  const forwardHeaders = ["authorization", "x-dev-bypass", "accept"];
  forwardHeaders.forEach((h) => {
    const value = request.headers.get(h);
    if (value) headers.set(h, value);
  });

  // Make the proxied request
  const fetchOptions: RequestInit = {
    method: request.method,
    headers,
  };

  // Include body for non-GET requests
  if (request.method !== "GET" && request.method !== "HEAD") {
    // Use arrayBuffer for binary-safe body transfer (handles multipart/form-data)
    const bodyBuffer = await request.arrayBuffer();
    if (bodyBuffer.byteLength > 0) {
      fetchOptions.body = bodyBuffer;
    }
  }

  try {
    const response = await fetch(url.toString(), fetchOptions);

    // Handle streaming responses (SSE)
    if (response.headers.get("content-type")?.includes("text/event-stream")) {
      return new NextResponse(response.body, {
        status: response.status,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    // Build response headers
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      // Skip hop-by-hop headers
      if (!["transfer-encoding", "connection"].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    // Handle 204 No Content - cannot have a body
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        headers: responseHeaders,
      });
    }

    // Get response body for other status codes
    const responseBody = await response.text();

    return new NextResponse(responseBody, {
      status: response.status,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error("Proxy error:", error);
    return NextResponse.json(
      { detail: "Backend service unavailable" },
      { status: 503 },
    );
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  return proxyRequest(request, path);
}
