import { useEffect, useState } from 'react';
import { getAuth, setAuth } from './api';
import Login from './components/Login';
import TimetablePage from './components/TimetablePage';
import StaffPage from './components/StaffPage';
import SectionsPage from './components/SectionsPage';
import CampusPage from './components/CampusPage';
import RequirementsPage from './components/RequirementsPage';
import WorkloadPage from './components/WorkloadPage';

const TABS = [
  ['timetable', 'Timetable', TimetablePage],
  ['requirements', 'Subject Load', RequirementsPage],
  ['workload', 'Lecturer Workload', WorkloadPage],
  ['staff', 'Staff', StaffPage],
  ['sections', 'Sections', SectionsPage],
  ['campuses', 'Campuses & Periods', CampusPage],
];

export default function App() {
  const [auth, setAuthState] = useState(getAuth());
  const [tab, setTab] = useState('timetable');

  useEffect(() => {
    const onLogout = () => setAuthState(null);
    window.addEventListener('vagdevi-logout', onLogout);
    return () => window.removeEventListener('vagdevi-logout', onLogout);
  }, []);

  if (!auth) {
    return <Login onLogin={(a) => { setAuth(a); setAuthState(a); }} />;
  }

  const Page = TABS.find(([k]) => k === tab)[2];
  return (
    <div>
      <header className="masthead">
        <h1>Vagdevi Junior College</h1>
        <span className="year">Timetable 2026-27</span>
        <div className="who">
          <span className={'role-chip' + (auth.role === 'ADMIN' ? ' admin' : '')}>
            {auth.role}
          </span>
          <span>{auth.username}</span>
          <button className="btn small"
            onClick={() => { setAuth(null); setAuthState(null); }}>
            Log out
          </button>
        </div>
      </header>
      <nav className="tabs" aria-label="Main">
        {TABS.map(([key, label]) => (
          <button key={key} className={tab === key ? 'active' : ''}
            onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>
      <main className="page">
        <Page role={auth.role} />
      </main>
    </div>
  );
}
