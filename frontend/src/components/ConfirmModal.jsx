import { useEffect, useState } from 'react';

// Modal de confirmação padronizada do painel admin (substitui o
// confirm() nativo do navegador). Fecha no ESC ou clicando fora.
export default function ConfirmModal({
  titulo = 'Confirmar exclusão',
  mensagem = 'Essa ação não pode ser desfeita.',
  detalhe = '',
  confirmarTexto = 'Excluir',
  onConfirm,
  onClose,
}) {
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape' && !busy) onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [busy, onClose]);

  const confirmar = async () => {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-overlay show" onClick={() => { if (!busy) onClose(); }}>
      <div
        className="modal modal-confirm"
        role="alertdialog"
        aria-modal="true"
        aria-label={titulo}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-body">
          <div className="confirm-icon" aria-hidden="true">🗑</div>
          <h3 className="modal-title">{titulo}</h3>
          <p className="modal-text">{mensagem}</p>
          {detalhe && <p className="confirm-item">{detalhe}</p>}
          <div className="confirm-actions">
            <button type="button" className="btn btn-ghost" disabled={busy} onClick={onClose}>
              Cancelar
            </button>
            <button type="button" className="btn btn-danger" disabled={busy} onClick={confirmar}>
              {busy ? 'Excluindo…' : confirmarTexto}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
