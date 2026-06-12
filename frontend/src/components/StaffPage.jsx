import { useEffect, useState } from 'react';
import { api } from '../api';

export default function StaffPage({ role }) {
  const [staff, setStaff] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [campuses, setCampuses] = useState([]);
  const [editing, setEditing] = useState(null);
  const [availEditing, setAvailEditing] = useState(null); // staff object
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

  const campusNames = (ids) => {
    if (!ids || !ids.length) return '-';
    return ids.map((id) => campuses.find((c) => c.id === id)?.name || id).join(', ');
  };

  return (
    <div>
      <div className="toolbar">
        <div className="note">
          {staff.length} profiles. JL rows supervise study hours.
          {!isAdmin && ' Salary and interview details are visible to admin only.'}
        </div>
        <div className="spacer" />
        <button className="btn" onClick={() => window.print()}>Print</button>
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
              <th>Employment</th><th>Home campus(es)</th><th>Phone</th>
              {isAdmin && <><th>Salary</th><th>Interview</th><th>Campaign place</th></>}
              <th>Active</th><th className="no-print"></th>
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
                <td>{campusNames(s.home_campus_ids)}</td>
                <td className="mono">{s.phone_number || '-'}</td>
                {isAdmin && <>
                  <td className="num">{s.salary_discussed ?? '-'}</td>
                  <td className="mono">{s.date_of_interview || '-'}</td>
                  <td>{s.campaign_village_town || '-'}</td>
                </>}
                <td>{s.active ? 'Yes' : <span className="under">No</span>}</td>
                <td style={{ whiteSpace: 'nowrap' }} className="no-print">
                  <button className="btn small" onClick={() => setEditing(s)}>Edit</button>{' '}
                  <button className="btn small" onClick={() => setAvailEditing(s)} title="Set availability">Avail</button>{' '}
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
      {availEditing && (
        <AvailabilityEditor staff={availEditing} campuses={campuses}
          onClose={() => setAvailEditing(null)} />
      )}
    </div>
  );
}

function StaffEditor({ staffRow, subjects, campuses, isAdmin, onClose, onSaved }) {
  const [f, setF] = useState(() => staffRow ? {
    name: staffRow.name, code: staffRow.code,
    phone_number: staffRow.phone_number || '',
    role: staffRow.role, employment: staffRow.employment,
    home_campus_ids: staffRow.home_campus_ids || [],
    active: staffRow.active,
    subject_ids: staffRow.subjects.map((s) => s.id),
    salary_discussed: staffRow.salary_discussed ?? '',
    date_of_interview: staffRow.date_of_interview || '',
    campaign_village_town: staffRow.campaign_village_town || '',
    notes_admin: staffRow.notes_admin || '',
  } : {
    name: '', code: '', phone_number: '', role: 'LECTURER',
    employment: 'FULL_TIME', home_campus_ids: [], active: true,
    subject_ids: [], salary_discussed: '', date_of_interview: '',
    campaign_village_town: '', notes_admin: '',
  });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  function toggleCampus(id) {
    const ids = f.home_campus_ids.includes(id)
      ? f.home_campus_ids.filter((x) => x !== id)
      : [...f.home_campus_ids, id];
    setF({ ...f, home_campus_ids: ids });
  }

  async function save() {
    setBusy(true); setErr('');
    const body = {
      ...f,
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
          <label className="fld">Phone
            <input type="text" value={f.phone_number} onChange={set('phone_number')} />
          </label>
          <label className="fld" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={f.active}
              onChange={(e) => setF({ ...f, active: e.target.checked })} />
            Active
          </label>
          <div className="fld wide">
            <span style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--ink-soft)' }}>
              Home campus(es)
            </span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 4 }}>
              {campuses.map((c) => (
                <label key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 13 }}>
                  <input type="checkbox" checked={f.home_campus_ids.includes(c.id)}
                    onChange={() => toggleCampus(c.id)} />
                  {c.name}
                </label>
              ))}
            </div>
          </div>
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

function AvailabilityEditor({ staff, campuses, onClose }) {
  const [allSlots, setAllSlots] = useState([]); // [{campus, slots}]
  const [blocked, setBlocked] = useState(new Set()); // slot ids that are blocked
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    Promise.all([
      api(`/staff/${staff.id}/availability`),
      ...campuses.map((c) =>
        api('/time-slots', { params: { campus_id: c.id } })
          .then((slots) => ({ campus: c, slots: slots.filter((s) => s.kind === 'PERIOD') }))
      ),
    ]).then(([avail, ...campusSlots]) => {
      setBlocked(new Set(avail.slot_ids_unavailable));
      setAllSlots(campusSlots);
    }).catch((e) => setErr(e.message));
  }, [staff.id, campuses]);

  function toggle(slotId) {
    const next = new Set(blocked);
    if (next.has(slotId)) next.delete(slotId); else next.add(slotId);
    setBlocked(next);
  }

  function blockAllForCampus(slots) {
    const next = new Set(blocked);
    slots.forEach((s) => next.add(s.id));
    setBlocked(next);
  }

  function clearAllForCampus(slots) {
    const next = new Set(blocked);
    slots.forEach((s) => next.delete(s.id));
    setBlocked(next);
  }

  async function save() {
    setBusy(true); setErr('');
    try {
      await api(`/staff/${staff.id}/availability`, {
        method: 'PUT',
        body: { slot_ids_unavailable: [...blocked] },
      });
      onClose();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  const totalBlocked = blocked.size;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={{ width: 580 }} onClick={(e) => e.stopPropagation()}>
        <h3>Blocked slots — {staff.code}</h3>
        <div className="sub">
          Click a slot to block it (red = blocked, white = available). Blocked slots
          are skipped by auto-assign and rejected on manual booking.
          {totalBlocked > 0 && <strong> {totalBlocked} slot{totalBlocked > 1 ? 's' : ''} blocked.</strong>}
        </div>
        {err && <div className="alert">{err}</div>}
        {allSlots.map(({ campus, slots }) => {
          if (!slots.length) return null;
          const campusBlocked = slots.filter((s) => blocked.has(s.id)).length;
          const allCampusBlocked = campusBlocked === slots.length;
          return (
            <div key={campus.id} style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                  textTransform: 'uppercase', color: 'var(--ink-soft)', letterSpacing: '0.06em' }}>
                  {campus.name}
                </span>
                {campusBlocked > 0 && (
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11,
                    color: 'var(--pen-red)' }}>
                    {campusBlocked}/{slots.length} blocked
                  </span>
                )}
                <button className="btn small" style={{ marginLeft: 'auto' }}
                  onClick={() => allCampusBlocked ? clearAllForCampus(slots) : blockAllForCampus(slots)}>
                  {allCampusBlocked ? 'Unblock all' : 'Block all'}
                </button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {slots.map((s) => {
                  const isBlocked = blocked.has(s.id);
                  return (
                    <button key={s.id} className="btn small"
                      style={{
                        fontFamily: 'var(--font-mono)',
                        background: isBlocked ? 'var(--pen-red-soft)' : 'var(--paper-raised)',
                        borderColor: isBlocked ? 'var(--pen-red)' : 'var(--rule-light)',
                        color: isBlocked ? 'var(--pen-red)' : 'var(--ink-soft)',
                      }}
                      onClick={() => toggle(s.id)}>
                      {isBlocked ? '✕ ' : ''}{s.label}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={busy}>Save</button>
        </div>
      </div>
    </div>
  );
}
