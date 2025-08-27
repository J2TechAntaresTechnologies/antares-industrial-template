import React, { useState } from 'react'
import { usePlc } from '../hooks/useApi.js'

export default function PlcDiag(){
  const api = usePlc()
  const [db, setDb] = useState(1)
  const [start, setStart] = useState(0)
  const [size, setSize] = useState(4)
  const [readRes, setReadRes] = useState(null)
  const [err, setErr] = useState(null)

  const [wStart, setWStart] = useState(0)
  const [wDb, setWDb] = useState(1)
  const [wData, setWData] = useState('')

  const doRead = async () => {
    try{
      setErr(null)
      const r = await api.read(db, start, size)
      setReadRes(r)
    }catch(e){
      setErr(String(e))
    }
  }

  const doWrite = async () => {
    if(wData.trim() === '') { setErr('data_b64 requerido'); return }
    try{
      setErr(null)
      const r = await api.write(wDb, wStart, wData.trim())
      alert('Escritura OK')
    }catch(e){
      setErr(String(e))
    }
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div className="card space-y-2">
        <div className="font-semibold">Lectura</div>
        <div className="flex gap-2 items-center">
          <label>DB</label><input type="number" value={db} onChange={e=>setDb(+e.target.value)} className="border rounded px-2 py-1 w-20"/>
          <label>Start</label><input type="number" value={start} onChange={e=>setStart(+e.target.value)} className="border rounded px-2 py-1 w-24"/>
          <label>Size</label><input type="number" value={size} onChange={e=>setSize(+e.target.value)} className="border rounded px-2 py-1 w-24"/>
          <button onClick={doRead} className="px-3 py-1 rounded bg-neutral-800 text-white">Leer</button>
        </div>
        <pre className="text-xs overflow-auto">{readRes? JSON.stringify(readRes, null, 2) : 'Sin lectura'}</pre>
      </div>

      <div className="card space-y-2">
        <div className="font-semibold">Escritura</div>
        <div className="flex gap-2 items-center flex-wrap">
          <label>DB</label><input type="number" value={wDb} onChange={e=>setWDb(+e.target.value)} className="border rounded px-2 py-1 w-20"/>
          <label>Start</label><input type="number" value={wStart} onChange={e=>setWStart(+e.target.value)} className="border rounded px-2 py-1 w-24"/>
        </div>
        <textarea value={wData} onChange={e=>setWData(e.target.value)} placeholder="data_b64" className="border rounded w-full h-28 p-2 font-mono"></textarea>
        <button onClick={doWrite} className="px-3 py-1 rounded bg-red-600 text-white">Escribir</button>
        <div className="text-xs text-neutral-600">Confirmación doble se implementará en la próxima iteración.</div>
      </div>

      {err && <div className="text-red-600 text-sm md:col-span-2">Error: {err}</div>}
    </div>
  )
}
