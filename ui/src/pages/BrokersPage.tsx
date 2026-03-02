import { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { useDevMode } from '../context/DevModeContext';
import { useToast } from '../context/ToastContext';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Pagination } from '../components/Pagination';
import { BrokerCard } from '../components/BrokerCard';
import { Modal } from '../components/Modal';
import { TabPanel } from '../components/TabPanel';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { formatDate } from '../utils';
import type { Broker, BrokerListItem } from '../types';

const PAGE_SIZE = 20;

export function BrokersPage() {
  const api = useApi();
  const toast = useToast();
  const devMode = useDevMode();
  const [brokers, setBrokers] = useState<BrokerListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('interactions');
  const [order, setOrder] = useState('desc');
  const [detailBroker, setDetailBroker] = useState<Broker | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ phone: string; name: string } | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const loadList = async (s?: string, p = page) => {
    try {
      const searchTerm = (s !== undefined ? s : search) || undefined;
      const result = await api.listBrokers(sortBy, order, searchTerm, (p - 1) * PAGE_SIZE, PAGE_SIZE);
      setBrokers(result.items);
      setTotal(result.total);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load brokers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadList(undefined, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortBy, order, page, devMode.active, devMode.brokers.length]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setLoading(true);
      setPage(1);
      loadList(value, 1);
    }, 300);
  };

  const handleCardClick = async (phone: string) => {
    try {
      const broker = await api.getBroker(phone);
      setDetailBroker(broker);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Failed to load broker', 'error');
    }
  };

  const toggleOrder = () => {
    setPage(1);
    setOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'));
  };

  const handleSortChange = (value: string) => {
    setPage(1);
    setSortBy(value);
  };

  return (
    <>
      <div className="toolbar">
        <h2>Corretores</h2>
        <div className="broker-controls">
          <input
            type="text"
            className="broker-search"
            placeholder="Buscar por nome..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
          />
          <select className="broker-sort" value={sortBy} onChange={(e) => handleSortChange(e.target.value)}>
            <option value="interactions">Mensagens</option>
            <option value="date_joined">Data de entrada</option>
            <option value="name">Nome</option>
            <option value="last_message_at">Ultima mensagem</option>
          </select>
          <button className="btn btn-secondary broker-order-btn" onClick={toggleOrder} title="Toggle order">
            {order === 'desc' ? '↓' : '↑'}
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner message="Carregando corretores..." />
      ) : error ? (
        <p style={{ color: 'var(--danger)' }}>Erro ao carregar corretores: {error}</p>
      ) : brokers.length === 0 ? (
        <div className="empty-state">
          <div className="icon">👤</div>
          <p>{search ? 'Nenhum corretor encontrado.' : 'Nenhum corretor cadastrado ainda.'}</p>
        </div>
      ) : (
        <>
          <div className="broker-grid">
            {brokers.map((b) => (
              <BrokerCard key={b.phone_number} broker={b} onClick={() => handleCardClick(b.phone_number)} />
            ))}
          </div>
          <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />
        </>
      )}

      {detailBroker && (
        <BrokerDetailModal
          broker={detailBroker}
          onClose={() => setDetailBroker(null)}
          onSaved={() => {
            setDetailBroker(null);
            toast('Corretor atualizado!', 'success');
            loadList(undefined, page);
          }}
          onDelete={() => {
            const b = detailBroker;
            setDetailBroker(null);
            setDeleteTarget({ phone: b.phone_number, name: b.name });
          }}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Deletar Corretor"
          message={
            <>
              Tem certeza que deseja deletar <strong>{deleteTarget.name}</strong>?
            </>
          }
          onConfirm={async () => {
            try {
              await api.deleteBroker(deleteTarget.phone);
              setDeleteTarget(null);
              toast('Corretor deletado', 'success');
              setPage(1);
              loadList(undefined, 1);
            } catch (err: unknown) {
              toast(err instanceof Error ? err.message : 'Falha ao deletar', 'error');
            }
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </>
  );
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function BrokerDetailModal({
  broker,
  onClose,
  onSaved,
  onDelete,
}: {
  broker: Broker;
  onClose: () => void;
  onSaved: () => void;
  onDelete: () => void;
}) {
  const api = useApi();
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState(broker.name);
  const [productLuxo, setProductLuxo] = useState(broker.product_type_luxo);
  const [productAlto, setProductAlto] = useState(broker.product_type_alto);
  const [productMedio, setProductMedio] = useState(broker.product_type_medio);
  const [productMcmv, setProductMcmv] = useState(broker.product_type_mcmv);
  const [sellInvestimento, setSellInvestimento] = useState(broker.sell_type_investimento);
  const [sellMoradia, setSellMoradia] = useState(broker.sell_type_moradia);
  const [regionNorte, setRegionNorte] = useState(broker.region_zona_norte);
  const [regionSul, setRegionSul] = useState(broker.region_zona_sul);
  const [regionCentral, setRegionCentral] = useState(broker.region_zona_central);
  const [soldProduct, setSoldProduct] = useState(broker.sold_delpro_product);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updates: Record<string, unknown> = {};
      if (name.trim() !== broker.name) updates.name = name.trim();
      if (productLuxo !== broker.product_type_luxo) updates.product_type_luxo = productLuxo;
      if (productAlto !== broker.product_type_alto) updates.product_type_alto = productAlto;
      if (productMedio !== broker.product_type_medio) updates.product_type_medio = productMedio;
      if (productMcmv !== broker.product_type_mcmv) updates.product_type_mcmv = productMcmv;
      if (sellInvestimento !== broker.sell_type_investimento) updates.sell_type_investimento = sellInvestimento;
      if (sellMoradia !== broker.sell_type_moradia) updates.sell_type_moradia = sellMoradia;
      if (regionNorte !== broker.region_zona_norte) updates.region_zona_norte = regionNorte;
      if (regionSul !== broker.region_zona_sul) updates.region_zona_sul = regionSul;
      if (regionCentral !== broker.region_zona_central) updates.region_zona_central = regionCentral;
      if (soldProduct !== broker.sold_delpro_product) updates.sold_delpro_product = soldProduct;

      if (Object.keys(updates).length === 0) {
        toast('Nenhuma alteracao para salvar', 'error');
        setSaving(false);
        return;
      }

      await api.updateBroker(broker.phone_number, updates);
      onSaved();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Falha ao salvar', 'error');
      setSaving(false);
    }
  };

  const profileTab = (
    <>
      <div className="form-group">
        <label>Nome</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="detail-row">
        <span className="label">Telefone</span>
        <span className="value">{broker.phone_number}</span>
      </div>
      <div className="detail-row">
        <span className="label">Mensagens enviadas</span>
        <span className="value">{broker.interactions}</span>
      </div>
      <div className="detail-row">
        <span className="label">Data de entrada</span>
        <span className="value">{formatDate(broker.date_joined)}</span>
      </div>
      <div className="detail-row">
        <span className="label">Ultima mensagem</span>
        <span className="value">{formatDate(broker.last_message_at)}</span>
      </div>
    </>
  );

  const preferencesTab = (
    <>
      <div className="checkbox-section">
        <h4>Tipo de Produto</h4>
        <div className="checkbox-group">
          <label>
            <input type="checkbox" checked={productLuxo} onChange={(e) => setProductLuxo(e.target.checked)} />
            Luxo
          </label>
          <label>
            <input type="checkbox" checked={productAlto} onChange={(e) => setProductAlto(e.target.checked)} />
            Alto Padrao
          </label>
          <label>
            <input type="checkbox" checked={productMedio} onChange={(e) => setProductMedio(e.target.checked)} />
            Medio Padrao
          </label>
          <label>
            <input type="checkbox" checked={productMcmv} onChange={(e) => setProductMcmv(e.target.checked)} />
            Minha Casa Minha Vida
          </label>
        </div>
      </div>

      <div className="checkbox-section">
        <h4>Tipo de Venda</h4>
        <div className="checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={sellInvestimento}
              onChange={(e) => setSellInvestimento(e.target.checked)}
            />
            Investimento
          </label>
          <label>
            <input type="checkbox" checked={sellMoradia} onChange={(e) => setSellMoradia(e.target.checked)} />
            Moradia
          </label>
        </div>
      </div>

      <div className="checkbox-section">
        <h4>Regiao de Atuacao</h4>
        <div className="checkbox-group">
          <label>
            <input type="checkbox" checked={regionNorte} onChange={(e) => setRegionNorte(e.target.checked)} />
            Zona Norte
          </label>
          <label>
            <input type="checkbox" checked={regionSul} onChange={(e) => setRegionSul(e.target.checked)} />
            Zona Sul
          </label>
          <label>
            <input type="checkbox" checked={regionCentral} onChange={(e) => setRegionCentral(e.target.checked)} />
            Zona Central
          </label>
        </div>
      </div>

      <div className="checkbox-section">
        <h4>Status</h4>
        <div className="checkbox-group">
          <label>
            <input type="checkbox" checked={soldProduct} onChange={(e) => setSoldProduct(e.target.checked)} />
            Vendeu produto Delpro
          </label>
        </div>
      </div>
    </>
  );

  return (
    <Modal
      onClose={onClose}
      title="Detalhes do Corretor"
      footer={
        <div className="modal-footer-actions">
          <button className="btn btn-primary" disabled={saving} onClick={handleSave}>
            {saving ? 'Salvando...' : 'Salvar'}
          </button>
          <button className="btn btn-danger" onClick={onDelete}>
            Deletar
          </button>
          <button className="btn btn-gray footer-cancel" onClick={onClose}>
            Cancelar
          </button>
        </div>
      }
    >
      <TabPanel
        tabs={[
          { id: 'profile', label: 'Perfil', content: profileTab },
          { id: 'preferences', label: 'Preferencias', content: preferencesTab },
        ]}
      />
    </Modal>
  );
}
