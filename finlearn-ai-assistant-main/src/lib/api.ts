// API Configuration
// DEV: talk directly to the local FastAPI server.
// PROD: use same-origin "/api" so Vercel can proxy requests to the backend
// without the browser hitting mixed-content errors.
export const API_URL =
  import.meta.env.DEV ? "http://localhost:8000" : "";

// Helper function for API calls
export async function apiCall<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}
