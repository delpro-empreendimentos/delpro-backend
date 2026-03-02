import type { BrokerListItem } from '../types';

function formatBrokerDate(dateStr: string): string {
  const d = new Date(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = d.getHours();
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const h12 = String(hours % 12 || 12).padStart(2, '0');
  return `${day}/${month}/${year} at ${h12}:${minutes} ${ampm}`;
}

interface BrokerCardProps {
  broker: BrokerListItem;
  onClick: () => void;
}

export function BrokerCard({ broker, onClick }: BrokerCardProps) {
  return (
    <div className="broker-card" onClick={onClick}>
      <div className="broker-avatar">{broker.name.charAt(0).toUpperCase()}</div>
      <div className="broker-info">
        <div className="broker-name">{broker.name}</div>
        <div className="broker-meta">{broker.interactions} mensagens</div>
        <div className="broker-meta">Joined: {formatBrokerDate(broker.date_joined)}</div>
        <div className="broker-meta">Last Message: {formatBrokerDate(broker.last_message_at)}</div>
      </div>
    </div>
  );
}
