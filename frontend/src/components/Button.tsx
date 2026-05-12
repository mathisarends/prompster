interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
}

export const Button = ({ variant = "primary", className = "", children, ...props }: ButtonProps) => {
  const base =
    variant === "primary"
      ? "cursor-pointer rounded-lg border border-[var(--beatline-gold-dark)] bg-[var(--beatline-gold)] px-4 py-2 text-sm font-semibold text-[#2D2D44] transition-colors hover:bg-[var(--beatline-gold-dark)]"
      : "cursor-pointer transition-colors hover:text-[var(--beatline-gold)]";

  return (
    <button type="button" className={`${base} ${className}`} {...props}>
      {children}
    </button>
  );
};
