export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  try {
    const p = await Promise.resolve(params);
    const path = Array.isArray(p.path) ? p.path.join('/') : '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_URL}/${path}${new URL(request.url).search}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    });

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('GET error:', error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  try {
    const p = await Promise.resolve(params);
    const path = Array.isArray(p.path) ? p.path.join('/') : '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_URL}/${path}`;
    const body = await request.json();

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    });

    const data = await response.json();
    const res = new Response(JSON.stringify(data), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    });

    const setCookie = response.headers.get('set-cookie');
    if (setCookie) {
      res.headers.set('set-cookie', setCookie);
    }

    return res;
  } catch (error) {
    console.error('POST error:', error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  try {
    const p = await Promise.resolve(params);
    const path = Array.isArray(p.path) ? p.path.join('/') : '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_URL}/${path}`;
    const body = await request.json();

    const response = await fetch(url, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
    });

    const data = await response.json();
    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('PATCH error:', error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> | { path: string[] } }
) {
  try {
    const p = await Promise.resolve(params);
    const path = Array.isArray(p.path) ? p.path.join('/') : '';
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const url = `${API_URL}/${path}`;

    const response = await fetch(url, {
      method: 'DELETE',
      credentials: 'include',
    });

    const data = response.status === 204 ? {} : await response.json();
    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('DELETE error:', error);
    return new Response(JSON.stringify({ error: String(error) }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
