import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';

// Edits one cell (section x period). Existing sessions can be removed or
// lock-toggled; a new booking supports subject + lecturer, half periods,
// study hour, and combining with other sections (one lecturer, many
// sections, exactly like "VJM merged in VJE1" on the paper sheet).
// Clashes come back from the API as a 409 and are shown in red, with the
// exact session that collided.
export default function CellEditor({ section, slot, sections, sessions,
  onClose, onChanged }) {
  const [subjects, setSubjects] = useState([]);
  const [staff, setStaff] = useState([]);
  const [subjectId, setSubjectId] = useState('');
  const [staffId, setStaffId] = useState('');
  const [half, setHalf] = useState('FULL');
  const [isSH, setIsSH] = useState(false);
  const [combineIds, setCombineIds] = useState([]);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api('/subjects'), api('/staff')])
      .then(([su, st]) => { setSubjects(su); setStaff(st); })
      .catch((e) => setErr(e.message));
  }, []);

  // When a subject is picked, only show lecturers who teach it.
  const eligibleStaff = useMemo(() => {
    if (isSH) return staff.filter((s) => s.role === 'JL' && s.active);
    if (!subjectId) return staff.filter((s) => s.active);
    return staff.filter((s) => s.active &&
      s.subjects.some((x) => x.id === +subjectId));
  }, [staff, subjectId, isSH]);

  useEffect(() => {
    // Reset lecturer if no longer eligible after a subject change.
    if (staffId && !eligibleStaff.some((s) => s.id === +staffId)) setStaffId('');
  }, [eligibleStaff, staffId]);

  async function save() {
    setBusy(true); setErr('');
    try {
      await api('/timetable/sessions', {
        method: 'POST',
        body: {
          time_slot_id: slot.id,
          section_ids: [section.id, ...combineIds.map(Number)],
          subject_id: isSH ? null : (subjectId ? +subjectId : null),
          staff_id: staffId ? +staffId : null,
          is_study_hour: isSH,
          half,
        },
      });
      onChanged();
      onClose();
    } catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function remove(id) {
    setBusy(true); setErr('');
    try {
      await api(`/timetable/sessions/${id}`, { method: 'DELETE' });
      onChanged();
      onClose();
    } catch (e) { setErr(e.message); setBusy(false); }
  }

  async function toggleLock(s) {
    try {
      await api(`/timetable/sessions/${s.id}/lock?locked=${!s.locked}`,
        { method: 'PUT' });
      onChanged();
      onClose();
    } catch (e) { setErr(e.message); }
  }

  const otherSections = sections.filter((s) => s.id !== section.id);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{section.name} - {slot.label}</h3>
        <div className="sub">Book a period, or manage what's already here.</div>

        {sessions.length > 0 && (
          <div style={{ marginBottom: 14 }}>
            {sessions.map((s) => (
              <div key={s.id} className="existing-session">
                <span className="grow">
                  {s.is_study_hour ? 'SH' : s.subject_code}
                  {' / '}{s.staff_code || '-'}
                  {s.half !== 'FULL' && ` (half ${s.half})`}
                  {s.section_ids.length > 1 && ' (combined)'}
                </span>
                <button className="btn small" onClick={() => toggleLock(s)}>
                  {s.locked ? 'Unlock' : 'Lock'}
                </button>
                <button className="btn small danger" onClick={() => remove(s.id)}>
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="form-grid">
          <label className="fld wide" style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <input type="checkbox" checked={isSH}
              onChange={(e) => setIsSH(e.target.checked)} />
            Study hour (supervised by a JL)
          </label>

          {!isSH && (
            <label className="fld">Subject
              <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}>
                <option value="">Pick...</option>
                {subjects.map((s) => (
                  <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
                ))}
              </select>
            </label>
          )}

          <label className="fld">{isSH ? 'Junior Lecturer' : 'Lecturer'}
            <select value={staffId} onChange={(e) => setStaffId(e.target.value)}>
              <option value="">{isSH ? 'Unassigned' : 'Pick...'}</option>
              {eligibleStaff.map((s) => (
                <option key={s.id} value={s.id}>{s.code} - {s.name}</option>
              ))}
            </select>
          </label>

          <label className="fld">Period portion
            <select value={half} onChange={(e) => setHalf(e.target.value)}>
              <option value="FULL">Full period</option>
              <option value="A">First half</option>
              <option value="B">Second half</option>
            </select>
          </label>

          {!isSH && (
            <label className="fld">Combine with (optional)
              <select multiple size={4} value={combineIds}
                onChange={(e) => setCombineIds(
                  [...e.target.selectedOptions].map((o) => o.value))}>
                {otherSections.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </label>
          )}
        </div>

        {err && <div className="alert">{err}</div>}
        <div className="note" style={{ margin: '10px 0' }}>
          Manual bookings are locked automatically so auto-assign keeps them.
        </div>
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn" onClick={onClose}>Close</button>
          <button className="btn primary" onClick={save}
            disabled={busy || (!isSH && !subjectId)}>
            Book period
          </button>
        </div>
      </div>
    </div>
  );
}
