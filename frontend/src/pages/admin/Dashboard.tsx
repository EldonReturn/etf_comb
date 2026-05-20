import { useState, useEffect } from 'react';

type TimeRange = '1m' | '3m' | '6m' | '1y' | '2y' | '3y' | '5y';

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: '1m', label: '1个月' },
  { value: '3m', label: '3个月' },
  { value: '6m', label: '6个月' },
  { value: '1y', label: '1年' },
  { value: '2y', label: '2年' },
  { value: '3y', label: '3年' },
  { value: '5y', label: '5年' },
];

interface SyncStatus {
  status: 'idle' | 'running';
  last_sync: string | null;
  last_result: 'success' | 'failed' | null;
}

interface DashboardProps {
  onLogout: () => void;
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [timeRange, setTimeRange] = useState<TimeRange>('1y');

  const fetchStatus = async () => {
    try {
      const response = await fetch('/api/admin/sync/status');
      if (response.ok) {
        const data = await response.json();
        setSyncStatus(data);
      }
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    setMessage(null);

    try {
      const response = await fetch('/api/admin/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ period: timeRange }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage({ type: 'success', text: data.message || '同步已启动' });
        await fetchStatus();
      } else {
        setMessage({ type: 'error', text: data.error || '同步失败' });
      }
    } catch {
      setMessage({ type: 'error', text: '网络错误' });
    } finally {
      setSyncing(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/admin/logout', { method: 'POST' });
    } catch {
      // ignore
    }
    onLogout();
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: '#f5f6fa',
      padding: '2rem'
    }}>
      <div style={{
        maxWidth: '800px',
        margin: '0 auto'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '2rem'
        }}>
          <h1 style={{ color: '#2c3e50', fontSize: '1.5rem' }}>ETF 管理后台</h1>
          <button
            onClick={handleLogout}
            style={{
              padding: '0.5rem 1rem',
              background: '#f5f6fa',
              border: '1px solid #dcdde1',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}
          >
            登出
          </button>
        </div>

        <div style={{
          background: '#ffffff',
          borderRadius: '8px',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
          padding: '2rem'
        }}>
          <h2 style={{ color: '#2c3e50', marginBottom: '1.5rem' }}>数据同步管理</h2>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1rem',
            marginBottom: '1.5rem'
          }}>
            <div style={{
              background: '#f5f6fa',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: '#7f8c8d', marginBottom: '0.5rem' }}>状态</div>
              <div style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: syncStatus?.status === 'running' ? '#3498db' : '#27ae60'
              }}>
                {syncStatus?.status === 'running' ? '同步中' : '空闲'}
              </div>
            </div>

            <div style={{
              background: '#f5f6fa',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: '#7f8c8d', marginBottom: '0.5rem' }}>上次同步</div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: '#2c3e50' }}>
                {syncStatus?.last_sync ? new Date(syncStatus.last_sync).toLocaleString() : '-'}
              </div>
            </div>

            <div style={{
              background: '#f5f6fa',
              padding: '1rem',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: '#7f8c8d', marginBottom: '0.5rem' }}>结果</div>
              <div style={{
                fontSize: '1rem',
                fontWeight: 600,
                color: syncStatus?.last_result === 'success' ? '#27ae60' :
                       syncStatus?.last_result === 'failed' ? '#e74c3c' : '#7f8c8d'
              }}>
                {syncStatus?.last_result === 'success' ? '成功' :
                 syncStatus?.last_result === 'failed' ? '失败' : '-'}
              </div>
            </div>
          </div>

          {message && (
            <div style={{
              background: message.type === 'success' ? 'rgba(39, 174, 96, 0.1)' : 'rgba(231, 76, 60, 0.1)',
              color: message.type === 'success' ? '#27ae60' : '#e74c3c',
              padding: '0.75rem',
              borderRadius: '8px',
              marginBottom: '1rem',
              fontSize: '0.875rem'
            }}>
              {message.text}
            </div>
          )}

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              style={{
                flex: 1,
                padding: '0.5rem',
                border: '1px solid #dcdde1',
                borderRadius: '8px',
                fontSize: '0.875rem',
                background: '#ffffff'
              }}
            >
              {TIME_RANGES.map((tr) => (
                <option key={tr.value} value={tr.value}>
                  {tr.label}
                </option>
              ))}
            </select>
            <button
              onClick={handleSync}
              disabled={syncing || syncStatus?.status === 'running'}
              style={{
                width: '100%',
                padding: '0.75rem',
                background: '#3498db',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '1rem',
                cursor: syncing || syncStatus?.status === 'running' ? 'not-allowed' : 'pointer',
                opacity: syncing || syncStatus?.status === 'running' ? 0.6 : 1
              }}
            >
              {syncing || syncStatus?.status === 'running' ? '同步中...' : '触发同步'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}