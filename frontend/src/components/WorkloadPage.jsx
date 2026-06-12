import { useEffect, useState } from 'react';
import { api } from '../api';

// Two live summaries:
// 1. Lecturer workload across ALL campuses (the handwritten "VVLN - 8" list).
// 2. Required vs scheduled per section, so under-scheduled sections show
//    in red pen before anyone prints the sheet.
export default function WorkloadPage() {
  const [staffLoad, setStaffLoad] = useState([]);
  const [campuses, setCampuses] = useState([]);
  const [campusId, setCampusId] = useState(null);
  const [sectionLoad, setSectionLoad] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    Promise.all([api('/workload/staff'), api('/campuses')])
      .then(([wl, cs]) => {
        setStaffLoad(wl); setCampuses(cs);
        if (cs.length) setCampusId(cs[0].id);
      }).catch((e) => setErr(e.message));
  }, []);

  useEffect(() => {
    if (!campusId) return;
    api('/workload/sections', { params: { campus_id: campusId } })
      .then(setSectionLoad).catch((e) => setErr(e.message));
  }, [campusId]);

  const fmt = (n) => Number(n).toLocaleString(undefined,
    { maximumFractionDigits: 1 }).replace('.5', '\u00bd');

  return (
    <div>
      {err && <div className="alert">{err}</div>}

      <h3 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', fontSize: 14 }}>
        Lecturer workload (all campuses)
      </h3>
      <div style={{ overflowX: 'auto', marginBottom: 26 }}>
        <table className="data" style={{ maxWidth: 760 }}>
          <thead>
            <tr><th>Code</th><th>Name</th><th>Role</th>
              <th>By subject</th><th>Total periods / day</th></tr>
          </thead>
          <tbody>
            {staffLoad.filter((s) => s.total > 0).map((s) => (
              <tr key={s.staff_id}>
                <td className="mono">{s.code}</td>
                <td>{s.name}</td>
                <td>{s.role}</td>
                <td className="mono">
                  {Object.entries(s.per_subject)
                    .map(([k, v]) => `${k} ${fmt(v)}`).join(', ')}
                </td>
                <td className="num">{fmt(s.total)}</td>
              </tr>
            ))}
            {staffLoad.every((s) => s.total === 0) && (
              <tr><td colSpan={5} className="muted">
                Nothing scheduled yet. Fill a timetable first.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>

      <h3 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', fontSize: 14 }}>
        Section coverage: required vs scheduled
      </h3>
      <div className="toolbar">
        <label className="fld">Campus
          <select value={campusId ?? ''} onChange={(e) => setCampusId(+e.target.value)}>
            {campuses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </label>
      </div>
      {sectionLoad && (
        <div style={{ overflowX: 'auto' }}>
          <table className="data">
            <thead>
              <tr>
                <th>Section</th>
                {sectionLoad.subjects.map((s) => <th key={s} className="mono">{s}</th>)}
                <th>SH</th><th>Required</th><th>Scheduled</th>
              </tr>
            </thead>
            <tbody>
              {sectionLoad.rows.map((r) => (
                <tr key={r.section_id}>
                  <td className="mono">{r.section}</td>
                  {sectionLoad.subjects.map((code) => {
                    const c = r.cells[code];
                    if (!c) return <td key={code} className="muted num">-</td>;
                    const short = c.scheduled < c.required;
                    return (
                      <td key={code} className={'num' + (short ? ' under' : ' exact')}
                        title={short ? 'Under-scheduled' : 'Covered'}>
                        {fmt(c.scheduled)}/{fmt(c.required)}
                      </td>
                    );
                  })}
                  <td className="num muted">{fmt(r.study_hours)}</td>
                  <td className="num">{fmt(r.total_required)}</td>
                  <td className={'num' +
                    (r.total_scheduled < r.total_required ? ' under' : ' exact')}>
                    {fmt(r.total_scheduled)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
