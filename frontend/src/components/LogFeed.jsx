import React, { useEffect, useState } from 'react';

export default function LogFeed() {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const id = setInterval(() => {
      // Placeholder for fetching logs
    }, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <section>
      <h2>Log Feed</h2>
      <ul>{logs.map((l, i) => <li key={i}>{l}</li>)}</ul>
    </section>
  );
}
