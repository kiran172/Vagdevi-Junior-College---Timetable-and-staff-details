import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import CellEditor from './CellEditor';

// Renders the grid exactly like the printed sheet: sections down the side,
// periods across the top, BREAK/LUNCH as vertical stacked-letter bands,
// each cell shows SUBJECT over lecturer code, split periods stacked with a
// divider, study hours in pencil gray.
export default function TimetablePage({ role }) {
  const [campuses, setCampuses] = useState([]);
  const [campusId, setCampusId] = useState(null);
  const [grid, setGrid] = useState(null);
  const [editing, setEditing] = useState(null); // {section, slot}
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null); // {kind, text}

  useEffect(() => {
    api('/campuses').then((cs) => {
      setCampuses(cs);
      if (cs.length && !campusId) setCampusId(cs[0].id);
    }).catch((e) => setMsg({ kind: 'err', text: e.message }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const load = useCallback(() => {
    if (!campusId) return;
    api('/timetable', { params: { campus_id: campusId } })
      .then(setGrid)
      .catch((e) => setMsg({ kind: 'err', text: e.message }));
  }, [campusId]);

  useEffect(() => { setPreview(null); setMsg(null); load(); }, [load]);

  async function runPreview() {
    setBusy(true); setMsg(null);
    try {
      const p = await api('/autoassign/preview', {
        method: 'POST',
        body: { campus_id: campusId, clear_existing: true },
      });
      setPreview(p);
    } catch (e) { setMsg({ kind: 'err', text: e.message }); }
    finally { setBusy(false); }
  }

  async function commit() {
    setBusy(true); setMsg(null);
    try {
      const r = await api('/autoassign/commit', {
        method: 'POST',
        body: { campus_id: campusId, clear_existing: true, proposal: preview.proposal },
      });
      setPreview(null);
      setMsg({ kind: 'ok', text: `Timetable filled: ${r.created} sessions. Manual (locked) entries were kept.` });
      load();
    } catch (e) { setMsg({ kind: 'err', text: e.message }); }
    finally { setBusy(false); }
  }

  async function clearCampus() {
    if (!window.confirm('Remove all unlocked sessions on this campus?')) return;
    try {
      const r = await api('/timetable/clear', {
        method: 'POST', params: { campus_id: campusId },
      });
      setMsg({ kind: 'ok', text: `Removed ${r.deleted} sessions.` });
      load();
    } catch (e) { setMsg({ kind: 'err', text: e.message }); }
  }

  if (!grid) return <div className="note">Loading timetable...</div>;

  const bandWord = { BREAK: 'BREAK', LUNCH: 'LUNCH BREAK', DINNER: 'DINNER BREAK' };

  return (
    <div>
      <div className="toolbar">
        <label className="fld">Campus
          <select value={campusId ?? ''} onChange={(e) => setCampusId(+e.target.value)}>
            {campuses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <div className="spacer" />
        <button className="btn no-print" onClick={() => window.print()}>Print</button>
        <button className="btn primary no-print" onClick={runPreview} disabled={busy}>
          Auto-assign (preview)
        </button>
        {role === 'ADMIN' && (
          <button className="btn danger no-print" onClick={clearCampus} disabled={busy}>
            Clear campus
          </button>
        )}
      </div>

      {msg && <div className={'alert' + (msg.kind === 'ok' ? ' ok' : '')}>{msg.text}</div>}

      {preview && (
        <div className="alert ok">
          <strong>Draft ready, nothing saved yet.</strong>{' '}
          {preview.stats.teaching_sessions} teaching sessions +{' '}
          {preview.stats.study_hours} study hours across {preview.stats.sections} sections.
          {preview.unfilled.length > 0 && (
            <>
              <div style={{ color: 'var(--pen-red)', marginTop: 6 }}>
                {preview.unfilled.length} requirement(s) could not be placed:
              </div>
              <ul className="unfilled">
                {preview.unfilled.map((u, i) => <li key={i}>{u}</li>)}
              </ul>
            </>
          )}
          <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
            <button className="btn primary" onClick={commit} disabled={busy}>
              Apply this draft
            </button>
            <button className="btn" onClick={() => setPreview(null)}>Discard</button>
          </div>
        </div>
      )}

      <div className="grid-wrap">
        <table className="tt">
          <thead>
            <tr>
              <th className="sec-h">Section</th>
              {grid.slots.map((s) => (
                <th key={s.id} className={s.kind !== 'PERIOD' ? 'band' : ''}>
                  {s.kind === 'PERIOD' ? s.label : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {grid.sections.map((sec) => (
              <tr key={sec.id}>
                <td className="sec-name">
                  {sec.name}
                  {sec.stream && <span className="stream">{sec.stream}</span>}
                </td>
                {grid.slots.map((slot) => {
                  if (slot.kind !== 'PERIOD') {
                    return (
                      <td key={slot.id} className="band">
                        <div className="stack">
                          {bandWord[slot.kind].split('').map((ch, i) =>
                            ch === ' ' ? <span key={i}>&nbsp;</span> : <span key={i}>{ch}</span>)}
                        </div>
                      </td>
                    );
                  }
                  const sessions = (grid.cells[sec.id]?.[slot.id]) || [];
                  const sorted = [...sessions].sort((a, b) =>
                    (a.half === 'B') - (b.half === 'B'));
                  return (
                    <td key={slot.id} className="cell"
                      onClick={() => setEditing({ section: sec, slot })}
                      title={`${sec.name} - ${slot.label}`}>
                      <div className="cell-inner">
                        {sorted.map((s) => (
                          <div key={s.id} className={'chip' + (s.is_study_hour ? ' sh' : '')}>
                            <span className="badges">
                              {s.locked && <span className="badge-lock" title="Locked: survives auto-assign">L</span>}
                              {s.section_ids.length > 1 && <span className="badge-comb" title="Combined class">+{s.section_ids.length - 1}</span>}
                            </span>
                            <span className="subj">{s.is_study_hour ? 'SH' : s.subject_code}</span>
                            <span className="who">{s.staff_code || '-'}</span>
                          </div>
                        ))}
                        {sorted.length === 0 && <div className="chip" />}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <CellEditor
          section={editing.section}
          slot={editing.slot}
          sections={grid.sections}
          sessions={(grid.cells[editing.section.id]?.[editing.slot.id]) || []}
          onClose={() => setEditing(null)}
          onChanged={() => { load(); }}
        />
      )}
    </div>
  );
}
