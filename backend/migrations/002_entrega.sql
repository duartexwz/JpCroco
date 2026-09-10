-- Migration: 002_entrega
-- Data: 2026-09-04
-- Descricao: Garante entrega 100% funcional — colunas de frete/endereco/rastreio
-- em pedidos, tamanho em itens_pedido e tabelas auxiliares de produto.
-- Idempotente: pode rodar em banco novo ou existente.

-- ---------- pedidos ----------
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS id_pedido VARCHAR(50);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS codigo_rastreio VARCHAR(50);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_envio TIMESTAMP;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS transportadora VARCHAR(50) DEFAULT 'Correios';
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS entrega_tipo VARCHAR(50) DEFAULT 'Correios';
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS valor_frete NUMERIC(10,2) DEFAULT 0.00;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS subtotal NUMERIC(10,2) DEFAULT 0.00;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS cep_destino VARCHAR(9);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS numero_pedido VARCHAR(50);

-- numero_pedido legado: preenche a partir de id_pedido quando vazio
UPDATE pedidos SET numero_pedido = id_pedido WHERE numero_pedido IS NULL AND id_pedido IS NOT NULL;
UPDATE pedidos SET id_pedido = numero_pedido WHERE id_pedido IS NULL AND numero_pedido IS NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pedidos_numero_pedido_key') THEN
        BEGIN
            ALTER TABLE pedidos ADD CONSTRAINT pedidos_numero_pedido_key UNIQUE (numero_pedido);
        EXCEPTION WHEN unique_violation THEN
            -- mantém sem constraint se houver duplicatas legadas
            NULL;
        END;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'pedidos_id_pedido_key') THEN
        BEGIN
            ALTER TABLE pedidos ADD CONSTRAINT pedidos_id_pedido_key UNIQUE (id_pedido);
        EXCEPTION WHEN unique_violation THEN
            NULL;
        END;
    END IF;
END $$;

-- ---------- itens_pedido ----------
ALTER TABLE itens_pedido ADD COLUMN IF NOT EXISTS tamanho VARCHAR(10);

-- ---------- produtos ----------
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS imagem TEXT;
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS preco_promocional NUMERIC(10,2);
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS ativo BOOLEAN DEFAULT TRUE;

-- ---------- produto_tamanhos ----------
CREATE TABLE IF NOT EXISTS produto_tamanhos (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    tamanho VARCHAR(10) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    preco NUMERIC(10,2)
);

-- ---------- produto_imagens ----------
CREATE TABLE IF NOT EXISTS produto_imagens (
    id SERIAL PRIMARY KEY,
    produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    ordem INTEGER NOT NULL DEFAULT 0
);

-- ---------- clientes ----------
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS cpf VARCHAR(14);

-- ---------- push_subscriptions (admin push) ----------
CREATE TABLE IF NOT EXISTS push_subscriptions (
    endpoint TEXT PRIMARY KEY,
    p256dh TEXT,
    auth TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
