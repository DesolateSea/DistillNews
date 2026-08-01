import { env } from "@/lib/env";
const API_URL = env.NEXT_PUBLIC_API_URL;

export type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  token?: string | null;
  useCache?: boolean;
  cacheTtlMs?: number;
  bypassCache?: boolean;
};

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const memoryCache = new Map<string, CacheEntry<unknown>>();

function getCacheKey(path: string, token?: string | null): string {
  return `api_cache:${token || "anon"}:${path}`;
}

export function clearApiCache(pathPrefix?: string) {
  if (!pathPrefix) {
    memoryCache.clear();
    if (typeof window !== "undefined" && window.sessionStorage) {
      try {
        Object.keys(sessionStorage).forEach((key) => {
          if (key.startsWith("api_cache:")) sessionStorage.removeItem(key);
        });
      } catch {
        // ignore storage errors
      }
    }
    return;
  }
  for (const key of memoryCache.keys()) {
    if (key.includes(pathPrefix)) memoryCache.delete(key);
  }
  if (typeof window !== "undefined" && window.sessionStorage) {
    try {
      Object.keys(sessionStorage).forEach((key) => {
        if (key.includes(pathPrefix)) sessionStorage.removeItem(key);
      });
    } catch {
      // ignore storage errors
    }
  }
}

function getApiUrl(path: string) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  let base = (process.env.NEXT_PUBLIC_API_URL || "__NEXT_PUBLIC_API_URL_PLACEHOLDER__").replace(/\/$/, "");
  if (!base || base === "__NEXT_PUBLIC_API_URL_PLACEHOLDER__") {
    base = "http://localhost:8000";
  }
  return `${base}${cleanPath}`;
}

export async function apiRequest<T>(
  path: string,
  { body, token, headers, useCache = true, cacheTtlMs = 180000, bypassCache = false, ...options }: ApiRequestOptions = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const isGet = method === "GET";
  const shouldCache = isGet && useCache !== false && !bypassCache;
  const cacheKey = getCacheKey(path, token);

  if (shouldCache) {
    const cached = memoryCache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < cacheTtlMs) {
      return cached.data as T;
    }
    if (typeof window !== "undefined" && window.sessionStorage) {
      try {
        const stored = sessionStorage.getItem(cacheKey);
        if (stored) {
          const parsed: CacheEntry<T> = JSON.parse(stored);
          if (Date.now() - parsed.timestamp < cacheTtlMs) {
            memoryCache.set(cacheKey, parsed);
            return parsed.data;
          }
        }
      } catch {
        // ignore storage errors
      }
    }
  }

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

  if (shouldCache && data !== null) {
    const entry: CacheEntry<T> = { data: data as T, timestamp: Date.now() };
    memoryCache.set(cacheKey, entry);
    if (typeof window !== "undefined" && window.sessionStorage) {
      try {
        sessionStorage.setItem(cacheKey, JSON.stringify(entry));
      } catch {
        // ignore quota errors
      }
    }
  }

  if (!isGet && (path.includes("preferences") || path.includes("track_time"))) {
    clearApiCache("/feeds");
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
  googleLogin: (params: { id_token?: string; access_token?: string; email?: string }) =>
    apiRequest<{ access_token: string }>("/google-login", {
      method: "POST",
      body: params,
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
  list: (token?: string | null, page?: number, limit?: number, category?: string | null) => {
    const p = page || 1;
    const l = limit || 20;
    const catQuery = category ? `?category=${encodeURIComponent(category)}` : "";
    return apiRequest<{ feeds: NewsItem[]; has_more?: boolean }>(
      `/feeds/${p}/${l}${catQuery}`,
      { token: token || undefined }
    );
  },
  search: (query: string, page?: number, limit?: number, category?: string | null, token?: string | null) => {
    const p = page || 1;
    const l = limit || 20;
    const catQuery = category ? `&category=${encodeURIComponent(category)}` : "";
    return apiRequest<{ feeds: NewsItem[]; has_more?: boolean; total?: number }>(
      `/feeds/search?q=${encodeURIComponent(query)}&page=${p}&limit=${l}${catQuery}`,
      { token: token || undefined }
    );
  },
  get: (articleId: string, token?: string | null) =>
    apiRequest<NewsItem>(`/feeds/${encodeURIComponent(articleId)}`, {
      token: token || undefined,
    }),
  trackTime: (articleId: string, durationMs: number, token?: string | null) =>
    apiRequest(`/feeds/${encodeURIComponent(articleId)}/track_time`, {
      method: "POST",
      token: token || undefined,
      body: { durationMs },
    }),
};

export const chatApi = {
  send: (message: string, token?: string | null) =>
    apiRequest<{ response?: string }>("/chat", {
      method: "POST",
      token: token || undefined,
      body: { message },
    }),
  sendArticleChat: (articleId: string, message: string, token?: string | null) =>
    apiRequest<{ response?: string }>(`/chat/${encodeURIComponent(articleId)}`, {
      method: "POST",
      token: token || undefined,
      body: { message },
    }),
};

export const weatherApi = {
  geocode: (location: string) =>
    apiRequest<Array<{ lat: number; lon: number }>>(
      `/weather/geocode?q=${encodeURIComponent(location)}&limit=1`
    ),
};

export function formatArticleDate(dateVal?: string | number): string {
  if (!dateVal || dateVal === "Unknown") return "Recently";
  try {
    if (typeof dateVal === "number") {
      const ms = dateVal < 1e11 ? dateVal * 1000 : dateVal;
      return new Date(ms).toLocaleDateString();
    }
    if (typeof dateVal === "string") {
      if (!isNaN(Number(dateVal))) {
        const num = Number(dateVal);
        const ms = num < 1e11 ? num * 1000 : num;
        return new Date(ms).toLocaleDateString();
      }
      const parsed = new Date(dateVal);
      if (!isNaN(parsed.getTime())) {
        return parsed.toLocaleDateString();
      }
    }
  } catch {
    // fallback
  }
  return "Recently";
}

export interface NewsItem {
  id: string;
  _id?: string;
  title: string;
  author: string;
  publication_date: string | number;
  summary: string;
  content: string;
  markdown_content?: string;
  category: string;
  tags: string[];
  source: {
    title?: string;
    name?: string;
    url?: string;
    created_utc?: number;
    subreddit?: string;
    media?: string[];
    content?: string;
    image_url?: string;
  };
  location?: string | null;
  duration?: number;
  popularity?: number;
}
