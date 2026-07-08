import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

interface ThemeToggleProps {
  variant?: "default" | "on-dark";
}

const ThemeToggle = ({ variant = "default" }: ThemeToggleProps) => {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  const className =
    variant === "on-dark"
      ? "inline-flex h-9 w-9 items-center justify-center rounded-lg border border-primary-foreground/30 bg-primary-foreground/10 text-primary-foreground transition-colors hover:bg-primary-foreground/20"
      : "inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-card text-foreground transition-colors hover:bg-muted";

  return (
    <button
      type="button"
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={className}
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
};

export default ThemeToggle;
