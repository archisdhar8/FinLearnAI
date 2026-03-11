// API Configuration
// DEV: localhost:8000
// Production: VITE_API_URL if set (direct to backend), else same-origin (vercel proxy)

export const API_URL =
  import.meta.env.DEV
    ? 'http://localhost:8000'
    : (import.meta.env.VITE_API_URL || '');

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
