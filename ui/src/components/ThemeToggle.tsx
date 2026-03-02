import { useTheme } from '../hooks/useTheme';

export function ThemeToggle() {
  const { isDark, toggle } = useTheme();

  return (
    <label className="theme-switch" title="Toggle dark mode">
      <input type="checkbox" checked={isDark} onChange={toggle} />
      <span className="theme-switch-track">
        <span className="theme-switch-icon theme-switch-moon">🌙</span>
        <span className="theme-switch-icon theme-switch-sun">☀️</span>
        <span className="theme-switch-thumb"></span>
      </span>
    </label>
  );
}
