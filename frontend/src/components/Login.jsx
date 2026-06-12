import { useState } from 'react';
import { api } from '../api';

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setErr('');
    try {
      const res = await api('/auth/login', {
        method: 'POST', body: { username, password },
      });
      onLogin(res);
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <h1>Vagdevi Junior College</h1>
        <div className="sub">Timetable system - sign in</div>
        <form onSubmit={submit}>
          <label className="fld">Username
            <input type="text" value={username} autoFocus
              onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label className="fld">Password
            <input type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </label>
          {err && <div className="alert">{err}</div>}
          <button className="btn primary" disabled={busy || !username || !password}>
            {busy ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}
