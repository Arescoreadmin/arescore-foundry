import React from 'react';

export default function CommandDeck({status, risks, onClone, onDiagnose}){
  return (
    <div className="p-4 space-y-4">
      <h2 className="text-xl font-bold">Command Deck</h2>
      <div className="grid grid-cols-3 gap-4">
        <div className="p-3 rounded border"><b>Health</b><pre>{JSON.stringify(status,null,2)}</pre></div>
        <div className="p-3 rounded border"><b>Risks</b><pre>{JSON.stringify(risks,null,2)}</pre></div>
        <div className="p-3 rounded border">
          <b>Actions</b>
          <div className="space-x-2 mt-2">
            <button onClick={onClone} className="px-3 py-1 rounded border">Clone Env</button>
            <button onClick={onDiagnose} className="px-3 py-1 rounded border">Diagnose</button>
          </div>
        </div>
      </div>
    </div>
  );
}