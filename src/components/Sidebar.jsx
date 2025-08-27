import React from 'react'

const LINKS = [
  { path: '/', label: 'Dashboard' },
  { path: '/parameters', label: 'Parámetros' },
  { path: '/plc', label: 'Diagnóstico PLC' },
  { path: '/logs', label: 'Logs' },
  { path: '/arneg', label: 'Arneg' },
  { path: '/ptz', label: 'PTZ' },
]

export default function Sidebar({route, onNavigate}){
  return (
    <aside className="row-start-2 col-start-1 bg-white border-r">
      <nav className="p-2">
        {LINKS.map(l => (
          <button key={l.path}
            onClick={() => onNavigate(l.path)}
            className={"w-full text-left sidebar-link " + (route===l.path?'active':'')}>
            {l.label}
          </button>
        ))}
      </nav>
    </aside>
  )
}
