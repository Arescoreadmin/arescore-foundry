export const getStatus = async () => (await fetch('/api/observer/status')).json();
export const getRisks = async () => (await fetch('/api/observer/risks')).json();