import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Newspaper } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4">
      <div className="text-center max-w-md">
        <Newspaper className="h-16 w-16 text-primary mx-auto mb-4 opacity-70" />
        <h1 className="text-4xl font-bold mb-2">404</h1>
        <h2 className="text-xl font-semibold mb-4">Page Not Found</h2>
        <p className="text-muted-foreground text-sm mb-6">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link href="/dashboard">
          <Button>Back to News Feed</Button>
        </Link>
      </div>
    </div>
  );
}
