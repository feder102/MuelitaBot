async function proxyRequest(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  try {
    const p = await Promise.resolve(params);
    const path = Array.isArray(p.path) ? p.path.join('/') : '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_URL}/${path}${new URL(request.url).search}`;
    const cookie = request.headers.get('cookie');
    const contentType = request.headers.get('content-type');
    const headers = new Headers();

    if (cookie) {
      headers.set('cookie', cookie);
    }
    if (contentType) {
      headers.set('content-type', contentType);
    }

    const body =
      request.method === 'GET' || request.method === 'DELETE'
        ? undefined
        : await request.text();

    const response = await fetch(url, {
      method: request.method,
      headers,
      body,
    });

    const responseBody = response.status === 204 ? '' : await response.text();
    const proxiedResponse = new Response(responseBody, {
      status: response.status,
      headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' },
    });

    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      proxiedResponse.headers.set('set-cookie', setCookie);
    }

    return proxiedResponse;
  } catch (error) {
    console.error(`${request.method} error:`, error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function GET(
  request: Request,
  context: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function POST(
  request: Request,
  context: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function PATCH(
  request: Request,
  context: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  return proxyRequest(request, context);
}

export async function DELETE(
  request: Request,
  context: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  return proxyRequest(request, context);
}
