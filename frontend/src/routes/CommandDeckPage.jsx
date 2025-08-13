import React, {useEffect, useState} from 'react';
import CommandDeck from '../components/CommandDeck';
import {getStatus, getRisks} from '../api/observer';
import {cloneEnv} from '../api/orchestrator';
import {diagnose} from '../api/rca';

export default function CommandDeckPage(){
  const [status, setStatus] = useState({});
  const [risks, setRisks] = useState({});
  useEffect(()=>{ (async()=>{ setStatus(await getStatus()); setRisks(await getRisks()); })(); },[]);
  return <CommandDeck status={status} risks={risks} onClone={async()=>alert(JSON.stringify(await cloneEnv()))} onDiagnose={async()=>alert(JSON.stringify(await diagnose()))} />
}