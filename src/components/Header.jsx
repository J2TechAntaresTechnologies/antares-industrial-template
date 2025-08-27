import React, { useEffect, useState } from 'react'
import { useHealth, usePlc } from '../hooks/useApi.js'
import StatusBadge from './StatusBadge.jsx'

export default function Header({onLogout, user}){
  const [env, setEnv] = useState('dev')
  const [plc, setPlc] = useState('unknown')
  const health = useHealth()
  const plcApi = usePlc()

  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const h = await health.fetch()
        if(!alive) return
        setEnv(h.env || 'dev')
      } catch {}
      // try {
      //   const p = await plcApi.ping()
      //   if(!alive) return
      //   if(p.plc === 'connected') setPlc('connected')
      //   else if(p.plc === 'disabled') setPlc('disabled')
      //   else setPlc('error')
      // } catch {
      //   setPlc('error')
      // }
    }
    tick()
    const id = setInterval(tick, 3000)
    return () => { alive = false; clearInterval(id) }
  }, [])

  return (
    <header className="col-span-2 row-start-1 h-16 flex items-center justify-between px-4 bg-white shadow">
      <div className="font-semibold">Antares Industrial UI</div>
      <div className="flex items-center gap-3">
        <span>Env: {env}</span>
        <StatusBadge status={plc} />
        <span className="text-sm text-neutral-600">Usuario: {user||'-'}</span>
        <button onClick={onLogout} className="px-3 py-1 rounded bg-neutral-200">Salir</button>
      </div>
    </header>
  )
}
