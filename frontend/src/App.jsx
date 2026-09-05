import { useEffect, useState } from 'react'
import './App.css'

const api = async (url, options = {}) => {
  const response = await fetch(url, { headers: { 'content-type': 'application/json' }, ...options })
  const data = await response.json()
  if (!response.ok) throw new Error(data.error || 'Request failed')
  return data
}

function App() {
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState(null)
  const [path, setPath] = useState('')
  const [scan, setScan] = useState(null)
  const [events, setEvents] = useState([])
  const [question, setQuestion] = useState('')
  const [sources, setSources] = useState([])
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  const loadProjects = () => api('/api/projects').then(setProjects).catch(e => setError(e.message))
  useEffect(() => {
    loadProjects()
  }, [])
  useEffect(() => {
    if (selected) api(`/api/projects/${selected._id}/events`).then(setEvents).catch(e => setError(e.message))
  }, [selected])

  const run = async (label, task) => {
    setBusy(label); setError('')
    try { await task() } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  const addProject = () => run('Connecting', async () => {
    const project = await api('/api/projects', { method: 'POST', body: JSON.stringify({ path }) })
    setSelected(project); setPath(''); await loadProjects()
  })
  const scanProject = () => run('Scanning', async () => {
    const result = await api(`/api/projects/${selected._id}/scan`, { method: 'POST', body: '{}' })
    setScan(result); setSelected(result.project); await loadProjects()
  })
  const analyze = () => run('Analyzing', async () => {
    await api(`/api/projects/${selected._id}/analyze`, { method: 'POST', body: JSON.stringify({ commit: 'HEAD' }) })
    setEvents(await api(`/api/projects/${selected._id}/events`))
  })
  const ask = () => run('Retrieving', async () => {
    const result = await api(`/api/projects/${selected._id}/query`, { method: 'POST', body: JSON.stringify({ question }) })
    setAnswer(result.answer)
    setSources(result.context || [])
  })

  const readiness = selected?.readiness?.checks
    ? selected.readiness
    : scan?.project?.readiness
  const readinessChecks = readiness?.checks ?? {}
  return <div className="shell">
    <aside>
      <div className="brand"><span>Y</span><div><strong>Yoshi</strong><small>Project Companion</small></div></div>
      <label>Connect repository</label>
      <input value={path} onChange={e => setPath(e.target.value)} placeholder={'D:\\projects\\my-app'} />
      <button onClick={addProject} disabled={!path || busy}>Add project</button>
      <nav>{projects.map(project => <button className={selected?._id === project._id ? 'active' : ''} key={project._id} onClick={() => { setSelected(project); setScan(null) }}>{project.name}<small>{project.path}</small></button>)}</nav>
    </aside>
    <main>
      <header><div><p>LOCAL-FIRST INTELLIGENCE</p><h1>{selected?.name || 'Choose a project'}</h1></div><div className="status"><i /> Ollama + MongoDB</div></header>
      {error && <div className="error">{error}</div>}
      {!selected ? <section className="empty"><h2>Your project memory starts here.</h2><p>Connect a local Git repository to inspect its history, documentation, readiness, and searchable knowledge.</p></section> : <>
        <div className="actions"><button onClick={scanProject} disabled={busy}>{busy === 'Scanning' ? busy : 'Scan & index'}</button><button onClick={analyze} disabled={busy}>{busy === 'Analyzing' ? busy : 'Analyze HEAD'}</button></div>
        <section className="metrics">
          <article><small>READINESS</small><strong>{readiness?.score ?? '—'}<em>%</em></strong><span>{readiness?.ready ? 'Ready for review' : 'Improvements available'}</span></article>
          <article><small>FILES INDEXED</small><strong>{scan?.memory?.chunks_indexed ?? '—'}</strong><span>Local searchable chunks</span></article>
          <article><small>COMMITS</small><strong>{scan?.commits?.length ?? '—'}</strong><span>Recent history loaded</span></article>
        </section>
        <div className="grid">
          <section className="panel"><div className="panel-title"><h2>Project timeline</h2><span>{events.length} events</span></div>{events.length ? events.map(event => <article className="event" key={event._id}><i /><div><strong>{event.analysis?.summary}</strong><p>{event.analysis?.reasoning}</p><small>{event.analysis?.change_type} · {event.analysis?.risk_level} risk · {event.commitHash?.slice(0, 8)}</small></div></article>) : <p className="muted">Analyze HEAD to create the first timeline event.</p>}</section>
          <section className="panel"><div className="panel-title"><h2>Readiness checks</h2></div>{Object.keys(readinessChecks).length ? Object.entries(readinessChecks).map(([name, ok]) => <div className="check" key={name}><span>{String(name).replaceAll('_', ' ')}</span><b className={ok ? 'pass' : 'fail'}>{ok ? 'PASS' : 'FIX'}</b></div>) : <p className="muted">Run a scan to audit the repository.</p>}</section>
        </div>
        <section className="panel ask"><div className="panel-title"><h2>Project knowledge</h2><span>Grounded retrieval</span></div><div className="askbar"><input value={question} onChange={e => setQuestion(e.target.value)} placeholder="Where is Ollama configured?"/><button onClick={ask} disabled={!question || busy}>Ask</button></div>{answer && <div className="answer">{answer}</div>}{sources.map(source => <article className="source" key={source.id}><strong>{source.source}</strong><p>{source.content.slice(0, 320)}{source.content.length > 320 ? '…' : ''}</p></article>)}</section>
      </>}
    </main>
  </div>
}

export default App
