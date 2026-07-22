import { cn } from "@/lib/utils";

type CardProps = {
  title?: string;
  description?: string;
  children?: React.ReactNode;
  className?: string;
};

export default function Card({
  title,
  description,
  children,
  className,
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm",
        "transition-shadow duration-200 hover:shadow-md",
        "dark:border-zinc-800 dark:bg-zinc-900",
        className,
      )}
    >
      {title ? (
        <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      ) : null}
      {description ? (
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          {description}
        </p>
      ) : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}
