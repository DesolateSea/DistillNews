declare global {
    interface Window {
        __ENV__?: {
            NEXT_PUBLIC_API_URL: string;
        };
    }
}

export const env = {
    get NEXT_PUBLIC_API_URL() {
        if (typeof window === "undefined") {
            return "";
        }

        return window.__ENV__?.NEXT_PUBLIC_API_URL ?? "";
    },
};