
type ButtonProps = {
  label: string;
  onClick?: () => void;
};

export default function Button({
  label,
  onClick,
}: ButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white hover:bg-blue-700 transition-colors"
    >
      {label}
    </button>
  );
}
