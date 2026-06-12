import { useEffect, useState } from 'react';
import { api } from '../api';

const toLabel = (min) => {
  const h = Math.floor(min / 60), m = min % 60;
  const hh = ((h + 11) % 12) + 1;
  return `${hh}.${String(m).padStart(2, '0')}`;
};

// Campuses and each campus's own period grid. Different campuses can have
// completely different timings (AC vs Saraswathi do): clash checks use the
// real start/end times, not column positions.
export default function CampusPage({ role }) {
  const isAdmin = role === 'ADMIN';
  const [campuses, setCampuses] = useState([]);
  const [campusId, setCampusId] = useState(null);
  const [slots, setSlots] = useState([]);
  const [editingSlot, setEditingSlot] = useState(null);
  const [err, setErr] = useState('');

  function loadCampuses() {
    api('/campuses').then((cs) => {
      setCampuses(cs);
      if (cs.length && !campusId) setCampusId(cs[0].id);
    }).catch((e) => setErr(e.message));
  }
  useEffect(loadCampuses, []);

  function loadSlots() {
    if (!campusId) return;
    api('/time-slots', { params: { campus_id: campusId } })
      .then(setSlots).catch((e) => setErr(e.message));
  }
  useEffect(loadSlots, [campusId]);

  async function addCampus() {
    const name = window.prompt('Campus name (e.g. New Bhavan):');
    if (!name) return;
    try { await api('/campuses', { method: 'POST', body: { name, location: 'Narasaraopet' } }); loadCampuses(); }
    catch (e) { setErr(e.message); }
  }

  async function removeSlot(s) {
    if (!window.confirm(`Delete the ${s.label} column?`)) return;
    try { await api(`/time-slots/${s.id}`, { method: 'DELETE' }); loadSlots(); }
    catch (e) { setErr(e.message); }
  }

  return (
    <div>
      <div className="toolbar">
        <label className="fld">Campus
          <select value={campusId ?? ''} onChange={(e) => setCampusId(+e.target.value)}>
            {campuses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <div className="spacer" />
        {isAdmin && <>
          <button className="btn" onClick={addCampus}>Add campus</button>
          <button className="btn primary" onClick={() => setEditingSlot('new')}>
            Add period / break
          </button>
        </>}
      </div>
      {!isAdmin && <div className="note" style={{ marginBottom: 10 }}>
        Period grid changes are admin-only. You can view the timings here.
      </div>}
      {err && <div className="alert">{err}</div>}
      <table className="data" style={{ maxWidth: 640 }}>
        <thead>
          <tr><th>#</th><th>Label</th><th>Starts</th><th>Ends</th><th>Type</th><th></th></tr>
        </thead>
        <tbody>
          {slots.map((s) => (
            <tr key={s.id}>
              <td className="num">{s.sort_order}</td>
              <td className="mono">{s.label}</td>
              <td className="mono">{toLabel(s.start_min)}</td>
              <td className="mono">{toLabel(s.end_min)}</td>
              <td>{s.kind === 'PERIOD' ? 'Period' :
                s.kind === 'LUNCH' ? 'Lunch break' :
                s.kind === 'DINNER' ? 'Dinner break' : 'Break'}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                {isAdmin && <>
                  <button className="btn small" onClick={() => setEditingSlot(s)}>Edit</button>{' '}
                  <button className="btn small danger" onClick={() => removeSlot(s)}>Delete</button>
                </>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editingSlot && (
        <SlotEditor row={editingSlot === 'new' ? null : editingSlot}
          campusId={campusId} nextOrder={slots.length}
          onClose={() => setEditingSlot(null)}
          onSaved={() => { setEditingSlot(null); loadSlots(); }} />
      )}
    </div>
  );
}

function SlotEditor({ row, campusId, nextOrder, onClose, onSaved }) {
  const [label, setLabel] = useState(row?.label || '');
  const [start, setStart] = useState(row ? minToHM(row.start_min) : '08:00');
  const [end, setEnd] = useState(row ? minToHM(row.end_min) : '08:45');
  const [kind, setKind] = useState(row?.kind || 'PERIOD');
  const [order, setOrder] = useState(row?.sort_order ?? nextOrder);
  const [err, setErr] = useState('');

  function minToHM(min) {
    return `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`;
  }
  function hmToMin(hm) {
    const [h, m] = hm.split(':').map(Number);
    return h * 60 + m;
  }

  async function save() {
    setErr('');
    const body = {
      campus_id: campusId, label,
      start_min: hmToMin(start), end_min: hmToMin(end),
      sort_order: +order, kind,
    };
    try {
      if (row) await api(`/time-slots/${row.id}`, { method: 'PUT', body });
      else await api('/time-slots', { method: 'POST', body });
      onSaved();
    } catch (e) { setErr(e.message); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{row ? `Edit ${row.label}` : 'Add period / break'}</h3>
        <div className="sub">Use 24-hour times. Labels are what print on the grid.</div>
        <div className="form-grid">
          <label className="fld">Label (e.g. 8.00-8.45)
            <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} />
          </label>
          <label className="fld">Type
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="PERIOD">Teaching period</option>
              <option value="BREAK">Break</option>
              <option value="LUNCH">Lunch break</option>
              <option value="DINNER">Dinner break</option>
            </select>
          </label>
          <label className="fld">Starts
            <input type="text" value={start} onChange={(e) => setStart(e.target.value)}
              placeholder="08:00" />
          </label>
          <label className="fld">Ends
            <input type="text" value={end} onChange={(e) => setEnd(e.target.value)}
              placeholder="08:45" />
          </label>
          <label className="fld">Column position
            <input type="number" value={order} onChange={(e) => setOrder(e.target.value)} />
          </label>
        </div>
        {err && <div className="alert">{err}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={!label}>Save</button>
        </div>
      </div>
    </div>
  );
}
