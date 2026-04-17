export async function POST(request: Request) {
  try {
    const { username, password } = await request.json();
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const response = await fetch(`${API_URL}/admin/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    return Response.json({
      ok: response.ok,
      status: response.status,
      data,
      apiUrl: API_URL,
      headers: Object.fromEntries(response.headers.entries()),
    });
  } catch (error) {
    return Response.json({
      error: String(error),
      message: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
