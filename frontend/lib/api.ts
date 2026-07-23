const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string | null;
};

function getApiUrl(path: string) {
  if (!API_URL) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not configured. Add it to frontend/.env.local or your production environment."
    );
  }

  return `${API_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function apiRequest<T>(
  path: string,
  { body, token, headers, ...options }: ApiRequestOptions = {}
): Promise<T> {
  const requestHeaders = new Headers(headers);
  if (body !== undefined) requestHeaders.set("Content-Type", "application/json");
  if (token) requestHeaders.set("Authorization", `Bearer ${token}`);

  const response = await fetch(getApiUrl(path), {
    ...options,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      data && typeof data === "object" && "message" in data
        ? String(data.message)
        : `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data as T;
}

export const authApi = {
  login: (email: string, password: string) =>
    apiRequest<{ access_token: string }>("/login", {
      method: "POST",
      body: { email, password },
    }),
  register: (email: string, password: string) =>
    apiRequest<{ access_token: string }>("/register", {
      method: "POST",
      body: { email, password },
    }),
  sendOtp: (email: string) =>
    apiRequest<{ message: string; session_token: string }>("/send-otp", {
      method: "POST",
      body: { email },
    }),
  verifyOtp: (email: string, otp: string, session_token: string) =>
    apiRequest<{ access_token: string }>("/verify-otp", {
      method: "POST",
      body: { email, otp, session_token },
    }),
};

export const preferencesApi = {
  get: (token: string) =>
    apiRequest<{ preferences: string[] }>("/preferences", { token }),
  save: (preferences: string[], token: string) =>
    apiRequest("/preferences", {
      method: "POST",
      token,
      body: { preferences },
    }),
};

export const feedsApi = {
  list: (token: string, page?: number, limit?: number) =>
    apiRequest<{ feeds: NewsItem[]; has_more?: boolean }>(
      page && limit ? `/feeds/${page}/${limit}` : "/feeds",
      { token }
    ),
  get: (articleId: string, token: string) =>
    apiRequest<NewsItem>(`/feeds/${encodeURIComponent(articleId)}`, { token }),
  trackTime: (articleId: string, durationMs: number, token: string) =>
    apiRequest(`/feeds/${encodeURIComponent(articleId)}/track_time`, {
      method: "POST",
      token,
      body: { durationMs },
    }),
};

export const chatApi = {
  send: (message: string, token: string) =>
    apiRequest<{ response?: string }>("/chat", {
      method: "POST",
      token,
      body: { message },
    }),
};

export const weatherApi = {
  geocode: (location: string) =>
    apiRequest<Array<{ lat: number; lon: number }>>(
      `/weather/geocode?q=${encodeURIComponent(location)}&limit=1`
    ),
};

export interface NewsItem {
  id: string;
  _id?: string;
  title: string;
  author: string;
  publication_date: string;
  summary: string;
  content: string;
  markdown_content?: string;
  category: string;
  tags: string[];
  source: {
    title: string;
    url: string;
    created_utc: number;
    subreddit: string;
    media: string[];
    content: string;
  };
  location?: string | null;
  duration?: number;
  popularity?: number;
}
