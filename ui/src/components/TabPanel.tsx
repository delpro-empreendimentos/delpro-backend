import { useState } from 'react';
import type { ReactNode } from 'react';

interface Tab {
  id: string;
  label: string;
  content: ReactNode;
}

interface TabPanelProps {
  tabs: Tab[];
  defaultTab?: string;
}

export function TabPanel({ tabs, defaultTab }: TabPanelProps) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

  return (
    <>
      <div className="modal-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`modal-tab${activeTab === tab.id ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div key={tab.id} className={`tab-content${activeTab === tab.id ? ' active' : ''}`}>
          {tab.content}
        </div>
      ))}
    </>
  );
}
