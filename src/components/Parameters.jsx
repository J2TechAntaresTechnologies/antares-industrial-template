import React, { useEffect, useMemo, useState } from 'react'
import { useParameters } from '../hooks/useApi.js'

export default function Parameters(){
  const api = useParameters()
  const [items, setItems] = useState([])
  const [q, setQ] = useState('')
  const [err, setErr] = useState(null)

  const load = async () => {
    try{
      const res = await api.list()
      setItems(res || [])
      setErr(null)
    }catch(e){
      setErr(String(e))
    }
  }

  useEffect(() => { load() }, [])

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase()
    if(!s) return items
    return items.filter(it => (it.key||'').toLowerCase().includes(s))
  }, [q, items])

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Buscar parámetro..." className="border rounded px-2 py-1 w-80"/>
        <button onClick={load} className="px-3 py-1 rounded bg-neutral-800 text-white">Refrescar</button>
      </div>
      {err && <div className="text-red-600 text-sm">Error: {err}</div>}
      <div className="card">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2">key</th>
              <th className="py-2">value</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((it) => (
              <tr key={it.key} className="border-b last:border-0">
                <td className="py-2 font-mono">{it.key}</td>
                <td className="py-2">{it.value}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan="2" className="text-center py-6 text-neutral-500">Sin resultados</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
