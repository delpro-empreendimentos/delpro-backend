import { NavLink } from 'react-router-dom';
import { ThemeToggle } from './ThemeToggle';
import { useDevMode } from '../context/DevModeContext';

export function Header() {
  const { active } = useDevMode();

  return (
    <header className="header">
      <h1>Delpro Admin</h1>
      <nav className="nav">
        <NavLink to="/documents" className={({ isActive }) => `nav-btn${isActive ? ' active' : ''}`}>
          Documents
        </NavLink>
        <NavLink to="/images" className={({ isActive }) => `nav-btn${isActive ? ' active' : ''}`}>
          Images
        </NavLink>
        <NavLink to="/prompt" className={({ isActive }) => `nav-btn${isActive ? ' active' : ''}`}>
          Agent Prompt
        </NavLink>
      </nav>
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '12px' }}>
        {active && <span className="dev-badge">DEV</span>}
        <ThemeToggle />
      </div>
    </header>
  );
}
