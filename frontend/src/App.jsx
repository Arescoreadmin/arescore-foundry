import React from 'react';
import WorldStatus from './components/WorldStatus.jsx';
import LogFeed from './components/LogFeed.jsx';
import ScenarioControls from './components/ScenarioControls.jsx';

export default function App() {
  return (
    <div>
      <h1>Sentinel Foundry Dashboard</h1>
      <WorldStatus />
      <LogFeed />
      <ScenarioControls />
    </div>
  );
}
