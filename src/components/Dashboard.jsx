import React, { useEffect, useState } from 'react'
import { useHealth } from '../hooks/useApi.js'

export default function Dashboard(){
  const api = useHealth()
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try{
        const h = await api.fetch()
        if(!alive) return
        setData(h)
        setErr(null)
      }catch(e){
        setErr(String(e))
      }
    }
    tick()
    const id = setInterval(tick, 3000)
    return () => { alive=false; clearInterval(id) }
  }, [])

  return (
    <div className="grid gap-4 grid-cols-1 md:grid-cols-3">
      <div className="card">
        <div className="font-semibold mb-2">Estado general</div>
        <pre className="text-sm">{JSON.stringify(data, null, 2)}</pre>
        {err && <div className="text-red-600 text-sm mt-2">Error: {err}</div>}
      </div>
      <div className="card">Alarmas activas: 0</div>
      <div className="card">KPIs: próximamente</div>
      <div className="card md:col-span-3">Últimos eventos: próximamente</div>
    </div>
  )
}
