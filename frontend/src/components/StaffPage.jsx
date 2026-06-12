import { useEffect, useState } from 'react';
import { api } from '../api';

// Lecturer + JL profiles. Operators see and edit the working fields;
// admin additionally sees salary / interview / campaign columns (the API
// never even sends those to an operator).
export default function StaffPage({ role }) {
  const [staff, setStaff] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [campuses, setCampuses] = useState([]);
  const [editing, setEditing] = useState(null); // staff object or 'new'
  const [err, setErr] = useState('');
  const isAdmin = role === 'ADMIN';

  function load() {
    Promise.all([api('/staff'), api('/subjects'), api('/campuses')])
      .then(([st, su, ca]) => { setStaff(st); setSubjects(su); setCampuses(ca); })
      .catch((e) => setErr(e.message));
  }
  useEffect(load, []);

  async function remove(s) {
    if (!window.confirm(`Delete ${s.name} (${s.code})?`)) return;
    try { await api(`/staff/${s.id}`, { method: 'DELETE' }); load(); }
    catch (e) { setErr(e.message); }
  }

  const campusName = (id) =>
    campuses.find((c) => c.id === id)?.name || '-';

  return (
    <div>
      <div className="toolbar">
        <div className="note">
          {staff.length} profiles. JL rows supervise study hours.
          {!isAdmin && ' Salary and interview details are visible to admin only.'}
        </div>
        <div className="spacer" />
        <button className="btn primary" onClick={() => setEditing('new')}>
          Add staff
        </button>
      </div>
      {err && <div className="alert">{err}</div>}
      <div style={{ overflowX: 'auto' }}>
        <table className="data">
          <thead>
            <tr>
              <th>Code</th><th>Name</th><th>Role</th><th>Subjects</th>
              <th>Employment</th><th>Home campus</th><th>Phone</th>
              {isAdmin && <><th>Salary</th><th>Interview</th><th>Campaign place</th></>}
              <th>Active</th><th></th>
            </tr>
          </thead>
          <tbody>
            {staff.map((s) => (
              <tr key={s.id}>
                <td className="mono">{s.code}</td>
                <td>{s.name}</td>
                <td>{s.role}</td>
                <td className="mono">{s.subjects.map((x) => x.code).join(', ') || '-'}</td>
                <td>{s.employment === 'FULL_TIME' ? 'Full time' : 'Part time'}</td>
                <td>{campusName(s.home_campus_id)}</td>
                <td className="mono">{s.phone_number || '-'}</td>
                {isAdmin && <>
                  <td className="num">{s.salary_discussed ?? '-'}</td>
                  <td className="mono">{s.date_of_interview || '-'}</td>
                  <td>{s.campaign_village_town || '-'}</td>
                </>}
                <td>{s.active ? 'Yes' : <span className="under">No</span>}</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  <button className="btn small" onClick={() => setEditing(s)}>Edit</button>{' '}
                  {isAdmin &&
                    <button className="btn small danger" onClick={() => remove(s)}>Delete</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {editing && (
        <StaffEditor staffRow={editing === 'new' ? null : editing}
          subjects={subjects} campuses={campuses} isAdmin={isAdmin}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load(); }} />
      )}
    </div>
  );
}

function StaffEditor({ staffRow, subjects, campuses, isAdmin, onClose, onSaved }) {
  const [f, setF] = useState(() => staffRow ? {
    name: staffRow.name, code: staffRow.code,
    phone_number: staffRow.phone_number || '',
    role: staffRow.role, employment: staffRow.employment,
    home_campus_id: staffRow.home_campus_id || '',
    active: staffRow.active,
    subject_ids: staffRow.subjects.map((s) => s.id),
    salary_discussed: staffRow.salary_discussed ?? '',
    date_of_interview: staffRow.date_of_interview || '',
    campaign_village_town: staffRow.campaign_village_town || '',
    notes_admin: staffRow.notes_admin || '',
  } : {
    name: '', code: '', phone_number: '', role: 'LECTURER',
    employment: 'FULL_TIME', home_campus_id: '', active: true,
    subject_ids: [], salary_discussed: '', date_of_interview: '',
    campaign_village_town: '', notes_admin: '',
  });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function save() {
    setBusy(true); setErr('');
    const body = {
      ...f,
      home_campus_id: f.home_campus_id ? +f.home_campus_id : null,
      salary_discussed: f.salary_discussed === '' ? null : +f.salary_discussed,
      date_of_interview: f.date_of_interview || null,
      campaign_village_town: f.campaign_village_town || null,
      notes_admin: f.notes_admin || null,
    };
    try {
      if (staffRow) await api(`/staff/${staffRow.id}`, { method: 'PUT', body });
      else await api('/staff', { method: 'POST', body });
      onSaved();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{staffRow ? `Edit ${staffRow.code}` : 'Add staff'}</h3>
        <div className="sub">Lecturer or Junior Lecturer profile</div>
        <div className="form-grid">
          <label className="fld">Name
            <input type="text" value={f.name} onChange={set('name')} />
          </label>
          <label className="fld">Code (on the grid)
            <input type="text" value={f.code} onChange={set('code')} />
          </label>
          <label className="fld">Role
            <select value={f.role} onChange={set('role')}>
              <option value="LECTURER">Lecturer</option>
              <option value="JL">Junior Lecturer (study hours)</option>
            </select>
          </label>
          <label className="fld">Employment
            <select value={f.employment} onChange={set('employment')}>
              <option value="FULL_TIME">Full time</option>
              <option value="PART_TIME">Part time</option>
            </select>
          </label>
          <label className="fld">Home campus
            <select value={f.home_campus_id} onChange={set('home_campus_id')}>
              <option value="">None</option>
              {campuses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </label>
          <label className="fld">Phone
            <input type="text" value={f.phone_number} onChange={set('phone_number')} />
          </label>
          <label className="fld wide">Subjects they teach
            <select multiple size={5} value={f.subject_ids.map(String)}
              onChange={(e) => setF({
                ...f,
                subject_ids: [...e.target.selectedOptions].map((o) => +o.value),
              })}>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
              ))}
            </select>
          </label>
          <label className="fld" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={f.active}
              onChange={(e) => setF({ ...f, active: e.target.checked })} />
            Active
          </label>
          {isAdmin && <>
            <label className="fld">Salary discussed (admin only)
              <input type="number" value={f.salary_discussed} onChange={set('salary_discussed')} />
            </label>
            <label className="fld">Date of interview (admin only)
              <input type="date" value={f.date_of_interview} onChange={set('date_of_interview')} />
            </label>
            <label className="fld wide">Campaign village / town (admin only)
              <input type="text" value={f.campaign_village_town} onChange={set('campaign_village_town')} />
            </label>
            <label className="fld wide">Admin notes
              <input type="text" value={f.notes_admin} onChange={set('notes_admin')} />
            </label>
          </>}
        </div>
        {err && <div className="alert">{err}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={save}
            disabled={busy || !f.name || !f.code}>Save</button>
        </div>
      </div>
    </div>
  );
}
