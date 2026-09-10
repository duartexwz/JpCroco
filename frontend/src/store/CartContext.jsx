import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const CartCtx = createContext(null);
const KEY = 'carrinho';

function load() {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) || '{}');
  } catch {
    return {};
  }
}

export function CartProvider({ children }) {
  const [itens, setItens] = useState(load);

  useEffect(() => {
    try {
      sessionStorage.setItem(KEY, JSON.stringify(itens));
    } catch { /* ignore */ }
  }, [itens]);

  const value = useMemo(() => {
    const arr = Object.entries(itens).map(([chave, item]) => ({
      chave,
      produto_id: parseInt(chave.split('::')[0], 10),
      ...item,
    }));
    const totalItens = Object.values(itens).reduce((s, i) => s + (i.quantidade || 0), 0);
    const subtotal = Object.values(itens).reduce((s, i) => s + (i.preco || 0) * (i.quantidade || 0), 0);

    const adicionar = (produto, tamanho = '') => {
      const chave = `${produto.id}::${tamanho || ''}`;
      setItens((prev) => {
        const atual = prev[chave];
        const maxqtd = produto.tamanhos?.length
          ? (produto.tamanhos.find((t) => t.tamanho === tamanho)?.stock ?? produto.stock ?? 99)
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
            stock: produto.tamanhos?.length
              ? (produto.tamanhos.find((t) => t.tamanho === tamanho)?.stock ?? produto.stock ?? 0)
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
