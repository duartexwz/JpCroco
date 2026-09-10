import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from './AuthContext';

const CartCtx = createContext(null);
const CHAVE_BASE = 'carrinho';
const ANONIMO = 'anonimo';

const chaveDe = (dono) => `${CHAVE_BASE}:${dono || ANONIMO}`;

function load(chave) {
  try {
    return JSON.parse(sessionStorage.getItem(chave) || '{}');
  } catch {
    return {};
  }
}

function save(chave, itens) {
  try {
    sessionStorage.setItem(chave, JSON.stringify(itens));
  } catch { /* ignore */ }
}

export function CartProvider({ children }) {
  // Carrinho POR USUÁRIO LOGADO: cada conta tem sua chave. Ao sair, a
  // conta anterior mantém o dela e quem entra vê só o próprio (ou vazio).
  const { user } = useAuth();
  const dono = user?.username || ANONIMO;
  const [itens, setItens] = useState(() => load(chaveDe(dono)));
  const donoRef = useRef(dono);
  if (donoRef.current !== dono) {
    // Troca de conta: guarda o carrinho do dono antigo e carrega o do novo.
    // Login vindo do anônimo: mescla o que já estava na sacola.
    const antigos = itens;
    save(chaveDe(donoRef.current), antigos);
    let novos = load(chaveDe(dono));
    if (donoRef.current === ANONIMO && dono !== ANONIMO && Object.keys(antigos).length) {
      novos = { ...novos };
      for (const [chave, item] of Object.entries(antigos)) {
        const atual = novos[chave];
        if (atual) {
          const max = Math.max(item.stock || atual.stock || 99, 1);
          novos[chave] = { ...atual, quantidade: Math.min((atual.quantidade || 0) + (item.quantidade || 0), max) };
        } else {
          novos[chave] = item;
        }
      }
      save(chaveDe(ANONIMO), {});
    }
    donoRef.current = dono;
    setItens(novos);
  }

  useEffect(() => {
    save(chaveDe(donoRef.current), itens);
  }, [itens]);

  const value = useMemo(() => {
    const arr = Object.entries(itens).map(([chave, item]) => ({
      chave,
      produto_id: parseInt(chave.split('::')[0], 10),
      ...item,
    }));
    const totalItens = Object.values(itens).reduce((s, i) => s + (i.quantidade || 0), 0);
    const subtotal = Object.values(itens).reduce((s, i) => s + (i.preco || 0) * (i.quantidade || 0), 0);

    const adicionar = (produto, tamanho = '', cor = '') => {
      const chave = `${produto.id}::${tamanho || ''}::${cor || ''}`;
      const acha = (ts) => (ts || []).find((t) => t.tamanho === tamanho && (t.cor || '') === (cor || ''));
      setItens((prev) => {
        const atual = prev[chave];
        const maxqtd = produto.tamanhos?.length
          ? (acha(produto.tamanhos)?.stock ?? produto.stock ?? 99)
          : (produto.stock ?? 99);
        if (atual) {
          return { ...prev, [chave]: { ...atual, quantidade: Math.min(atual.quantidade + 1, maxqtd) } };
        }
        return {
          ...prev,
          [chave]: {
            nome: produto.nome,
            preco: produto.preco_promocional ?? produto.preco,
            tamanho: tamanho || produto.tamanho || null,
            cor: cor || produto.cor || null,
            stock: produto.tamanhos?.length
              ? (acha(produto.tamanhos)?.stock ?? produto.stock ?? 0)
              : (produto.stock ?? 0),
            imagem: produto.imagem || produto.imagens?.[0] || null,
            quantidade: 1,
          },
        };
      });
    };
    const alterarQuantidade = (chave, novaQtd) => {
      setItens((prev) => {
        if (!prev[chave]) return prev;
        if (novaQtd <= 0) {
          const c = { ...prev };
          delete c[chave];
          return c;
        }
        return { ...prev, [chave]: { ...prev[chave], quantidade: Math.min(novaQtd, prev[chave].stock || 99) } };
      });
    };
    const remover = (chave) =>
      setItens((prev) => {
        const c = { ...prev };
        delete c[chave];
        return c;
      });
    const limpar = () => setItens({});

    return { itens, arr, totalItens, subtotal, adicionar, alterarQuantidade, remover, limpar };
  }, [itens]);

  return <CartCtx.Provider value={value}>{children}</CartCtx.Provider>;
}

export const useCart = () => useContext(CartCtx);
