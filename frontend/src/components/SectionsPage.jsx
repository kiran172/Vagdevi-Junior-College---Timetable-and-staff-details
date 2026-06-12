import { useEffect, useState } from 'react';
import { api } from '../api';

// Sections (classes) per campus: VJE1, VSE21, GJE2...
export default function SectionsPage({ role }) {
  const [campuses, setCampuses] = useState([]);
  const [campusId, setCampusId] = useState(null);
  const [sections, setSections] = useState([]);
  const [editing, setEditing] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    api('/campuses').then((cs) => {
      setCampuses(cs);
      if (cs.length) setCampusId(cs[0].id);
    }).catch((e) => setErr(e.message));
  }, []);

  function load() {
    if (!campusId) return;
    api('/sections', { params: { campus_id: campusId } })
      .then(setSections).catch((e) => setErr(e.message));
  }
  useEffect(load, [campusId]);

  async function remove(s) {
    if (!window.confirm(`Delete section ${s.name}? Its timetable entries go too.`)) return;
    try { await api(`/sections/${s.id}`, { method: 'DELETE' }); load(); }
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
        <button className="btn primary" onClick={() => setEditing('new')}>Add section</button>
      </div>
      {err && <div className="alert">{err}</div>}
      <table className="data" style={{ maxWidth: 560 }}>
        <thead>
          <tr><th>Order</th><th>Section</th><th>Stream</th><th></th></tr>
        </thead>
        <tbody>
          {sections.map((s) => (
            <tr key={s.id}>
              <td className="num">{s.sort_order}</td>
              <td className="mono">{s.name}</td>
              <td>{s.stream || '-'}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="btn small" onClick={() => setEditing(s)}>Edit</button>{' '}
                {role === 'ADMIN' &&
                  <button className="btn small danger" onClick={() => remove(s)}>Delete</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {editing && (
        <SectionEditor row={editing === 'new' ? null : editing}
          campusId={campusId} nextOrder={sections.length}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load(); }} />
      )}
    </div>
  );
}

function SectionEditor({ row, campusId, nextOrder, onClose, onSaved }) {
  const [name, setName] = useState(row?.name || '');
  const [stream, setStream] = useState(row?.stream || '');
  const [order, setOrder] = useState(row?.sort_order ?? nextOrder);
  const [err, setErr] = useState('');

  async function save() {
    setErr('');
    const body = { campus_id: campusId, name, stream, sort_order: +order };
    try {
      if (row) await api(`/sections/${row.id}`, { method: 'PUT', body });
      else await api('/sections', { method: 'POST', body });
      onSaved();
    } catch (e) { setErr(e.message); }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{row ? `Edit ${row.name}` : 'Add section'}</h3>
        <div className="form-grid">
          <label className="fld">Name (e.g. VJE21)
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="fld">Stream (MAINS / EAMCET / BIPC / CEC)
            <input type="text" value={stream} onChange={(e) => setStream(e.target.value)} />
          </label>
          <label className="fld">Row position on the grid
            <input type="number" value={order} onChange={(e) => setOrder(e.target.value)} />
          </label>
        </div>
        {err && <div className="alert">{err}</div>}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
          <button className="btn" onClick={onClose}>Cancel</button>
          <button className="btn primary" onClick={save} disabled={!name}>Save</button>
        </div>
      </div>
    </div>
  );
}
