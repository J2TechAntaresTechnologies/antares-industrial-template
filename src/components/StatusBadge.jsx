import React from 'react'

export default function StatusBadge({status}){
  if(status === 'connected') return <span className="badge ok">PLC: Connected</span>
  if(status === 'disabled') return <span className="badge dis">PLC: Disabled</span>
  if(status === 'error') return <span className="badge err">PLC: Error</span>
  return <span className="badge dis">PLC: Unknown</span>
}
