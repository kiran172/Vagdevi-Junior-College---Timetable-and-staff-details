import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';

// This is the digital version of the handwritten allocation sheet:
// periods per day of each subject for each section, in half-period steps
// (Sanskrit 1/2, EAMCET subjects 1 1/2...). Auto-assign reads this table.
export default function RequirementsPage() {
  const [campuses, setCampuses] = useState([]);
  const [campusId, setCampusId] = useState(null);
  const [sections, setSections] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [reqs, setReqs] = useState({});   // "sec-subj" -> halves
  const [err, setErr] = useState('');
  const [saved, setSaved] = useState('');

  useEffect(() => {
    Promise.all([api('/campuses'), api('/subjects')])
      .then(([cs, su]) => {
        setCampuses(cs); setSubjects(su);
        if (cs.length) setCampusId(cs[0].id);
      }).catch((e) => setErr(e.message));
  }, []);

  function load() {
    if (!campusId) return;
    Promise.all([
      api('/sections', { params: { campus_id: campusId } }),
      api('/requirements', { params: { campus_id: campusId } }),
    ]).then(([secs, rs]) => {
      setSections(secs);
      const map = {};
      rs.forEach((r) => { map[`${r.section_id}-${r.subject_id}`] = r.halves_per_day; });
      setReqs(map);
    }).catch((e) => setErr(e.message));
  }
  useEffect(load, [campusId]);

  async function setCell(sectionId, subjectId, halves) {
    setErr(''); setSaved('');
    try {
      await api('/requirements', {
        method: 'POST',
        body: { section_id: sectionId, subject_id: subjectId, halves_per_day: halves },
      });
      setReqs((r) => ({ ...r, [`${sectionId}-${subjectId}`]: halves }));
      setSaved('Saved');
      setTimeout(() => setSaved(''), 1500);
    } catch (e) { setErr(e.message); }
  }

  const totals = useMemo(() => {
    const bySubject = {}; let grand = 0;
    sections.forEach((sec) => subjects.forEach((su) => {
      const h = reqs[`${sec.id}-${su.id}`] || 0;
      bySubject[su.id] = (bySubject[su.id] || 0) + h;
      grand += h;
    }));
    return { bySubject, grand };
  }, [reqs, sections, subjects]);

  const fmt = (halves) => halves ? (halves / 2).toLocaleString(undefined,
    { maximumFractionDigits: 1 }).replace('.5', '\u00bd') : '-';

  return (
    <div>
      <div className="toolbar">
        <label className="fld">Campus
          <select value={campusId ?? ''} onChange={(e) => setCampusId(+e.target.value)}>
            {campuses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
        <div className="note">
          Periods per day, in half-period steps. Auto-assign fills the
          timetable from this sheet. 0 removes the requirement.
        </div>
        <div className="spacer" />
        {saved && <span className="exact mono">{saved}</span>}
      </div>
      {err && <div className="alert">{err}</div>}
      <div style={{ overflowX: 'auto' }}>
        <table className="data">
          <thead>
            <tr>
              <th>Section</th>
              {subjects.map((s) => <th key={s.id} className="mono">{s.code}</th>)}
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {sections.map((sec) => {
              const rowTotal = subjects.reduce(
                (acc, su) => acc + (reqs[`${sec.id}-${su.id}`] || 0), 0);
              return (
                <tr key={sec.id}>
                  <td className="mono">{sec.name}</td>
                  {subjects.map((su) => (
                    <td key={su.id} style={{ padding: 2 }}>
                      <select
                        value={reqs[`${sec.id}-${su.id}`] || 0}
                        onChange={(e) => setCell(sec.id, su.id, +e.target.value)}
                        style={{ border: 'none', width: '100%', background: 'transparent' }}>
                        {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((h) => (
                          <option key={h} value={h}>{h ? fmt(h) : '-'}</option>
                        ))}
                      </select>
                    </td>
                  ))}
                  <td className="num">{fmt(rowTotal)}</td>
                </tr>
              );
            })}
            <tr>
              <td><strong>Total</strong></td>
              {subjects.map((su) => (
                <td key={su.id} className="num">{fmt(totals.bySubject[su.id] || 0)}</td>
              ))}
              <td className="num"><strong>{fmt(totals.grand)}</strong></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
