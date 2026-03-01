/**
 * api.js - HTTP client for the Find That Book backend API.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const REQUEST_TIMEOUT_MS = 30000;

export async function searchBooks(query) {
  const url = `${API_BASE_URL}/api/search`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ query }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({ detail: `Status ${response.status}` }));
      throw new ApiError(errorBody.detail || `Request failed`, response.status);
    }
    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof ApiError) throw error;
    if (error.name === "AbortError") throw new ApiError("Request timed out.", 408, "TIMEOUT");
    throw new ApiError("Unable to connect to the search service.", 0, "NETWORK_ERROR");
  }
}

export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch { return false; }
}

export class ApiError extends Error {
  constructor(message, statusCode, errorCode = null) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.errorCode = errorCode;
  }
}
