--
-- PostgreSQL database dump
--

\restrict AclpYKiLs5KJF6wponnGEEshNHod4382cWKE0c45pCzLW01JGJBlEIpvRhrJqbD

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admins; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.admins (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    password character varying(150) NOT NULL,
    acesso character varying(10) NOT NULL,
    nome_completo character varying DEFAULT ''::character varying
);


ALTER TABLE public.admins OWNER TO loja_admin;

--
-- Name: admins_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.admins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.admins_id_seq OWNER TO loja_admin;

--
-- Name: admins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.admins_id_seq OWNED BY public.admins.id;


--
-- Name: clientes; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.clientes (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    email character varying(150) NOT NULL,
    telefone character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    cpf character varying(14)
);


ALTER TABLE public.clientes OWNER TO loja_admin;

--
-- Name: clientes_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.clientes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clientes_id_seq OWNER TO loja_admin;

--
-- Name: clientes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.clientes_id_seq OWNED BY public.clientes.id;


--
-- Name: consentimentos; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.consentimentos (
    id integer NOT NULL,
    cliente_id integer,
    email character varying(150),
    ip character varying(45),
    versao character varying(10) NOT NULL,
    necessarios boolean DEFAULT true,
    analiticos boolean DEFAULT false,
    marketing boolean DEFAULT false,
    aceitou boolean NOT NULL,
    criado_em timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.consentimentos OWNER TO loja_admin;

--
-- Name: consentimentos_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.consentimentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.consentimentos_id_seq OWNER TO loja_admin;

--
-- Name: consentimentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.consentimentos_id_seq OWNED BY public.consentimentos.id;


--
-- Name: itens_pedido; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.itens_pedido (
    id integer NOT NULL,
    pedido_id integer NOT NULL,
    produto_id integer NOT NULL,
    quantidade integer NOT NULL,
    preco_unitario numeric(10,2) NOT NULL,
    tamanho character varying(10),
    CONSTRAINT itens_pedido_quantidade_check CHECK ((quantidade > 0))
);


ALTER TABLE public.itens_pedido OWNER TO loja_admin;

--
-- Name: itens_pedido_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.itens_pedido_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.itens_pedido_id_seq OWNER TO loja_admin;

--
-- Name: itens_pedido_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.itens_pedido_id_seq OWNED BY public.itens_pedido.id;


--
-- Name: pedidos; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.pedidos (
    id integer NOT NULL,
    cliente_id integer NOT NULL,
    data_pedido timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    status character varying(30) NOT NULL,
    endereco_entrega text NOT NULL,
    id_pedido character varying(50) NOT NULL,
    valor_total numeric(10,2) DEFAULT 0.00 NOT NULL,
    codigo_rastreio character varying(50),
    data_envio timestamp without time zone,
    transportadora character varying(50) DEFAULT 'Correios'::character varying,
    entrega_tipo character varying(20) DEFAULT 'Correios'::character varying
);


ALTER TABLE public.pedidos OWNER TO loja_admin;

--
-- Name: pedidos_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.pedidos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.pedidos_id_seq OWNER TO loja_admin;

--
-- Name: pedidos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.pedidos_id_seq OWNED BY public.pedidos.id;


--
-- Name: produto_imagens; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.produto_imagens (
    id integer NOT NULL,
    produto_id bigint NOT NULL,
    url text NOT NULL,
    ordem integer DEFAULT 0 NOT NULL,
    criado_em timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.produto_imagens OWNER TO loja_admin;

--
-- Name: produto_imagens_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.produto_imagens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.produto_imagens_id_seq OWNER TO loja_admin;

--
-- Name: produto_imagens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.produto_imagens_id_seq OWNED BY public.produto_imagens.id;


--
-- Name: produto_tamanhos; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.produto_tamanhos (
    id integer NOT NULL,
    produto_id bigint NOT NULL,
    tamanho character varying(10) NOT NULL,
    stock integer DEFAULT 0 NOT NULL,
    preco numeric(10,2),
    criado_em timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT produto_tamanhos_preco_check CHECK ((preco >= (0)::numeric)),
    CONSTRAINT produto_tamanhos_stock_check CHECK ((stock >= 0))
);


ALTER TABLE public.produto_tamanhos OWNER TO loja_admin;

--
-- Name: produto_tamanhos_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.produto_tamanhos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.produto_tamanhos_id_seq OWNER TO loja_admin;

--
-- Name: produto_tamanhos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.produto_tamanhos_id_seq OWNED BY public.produto_tamanhos.id;


--
-- Name: produtos; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.produtos (
    id bigint NOT NULL,
    nome character varying(100) NOT NULL,
    preco numeric(10,2) NOT NULL,
    tamanho character varying(10),
    stock integer DEFAULT 0 NOT NULL,
    ativo boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    imagem text,
    preco_promocional numeric(10,2),
    peso_gramas integer DEFAULT 500,
    comprimento integer DEFAULT 20,
    largura integer DEFAULT 15,
    altura integer DEFAULT 10,
    diametro integer DEFAULT 0,
    tp_objeto integer DEFAULT 2,
    CONSTRAINT produtos_preco_check CHECK ((preco >= (0)::numeric)),
    CONSTRAINT produtos_stock_check CHECK ((stock >= 0))
);


ALTER TABLE public.produtos OWNER TO loja_admin;

--
-- Name: produtos_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

ALTER TABLE public.produtos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.produtos_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.schema_migrations (
    version character varying(50) NOT NULL,
    applied_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.schema_migrations OWNER TO loja_admin;

--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    username character varying(150) NOT NULL,
    password character varying(200) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    acesso character varying(10) NOT NULL,
    nome_completo character varying DEFAULT ''::character varying
);


ALTER TABLE public.usuarios OWNER TO loja_admin;

--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuarios_id_seq OWNER TO loja_admin;

--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.usuarios_id_seq OWNED BY public.usuarios.id;


--
-- Name: admins id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.admins ALTER COLUMN id SET DEFAULT nextval('public.admins_id_seq'::regclass);


--
-- Name: clientes id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.clientes ALTER COLUMN id SET DEFAULT nextval('public.clientes_id_seq'::regclass);


--
-- Name: consentimentos id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.consentimentos ALTER COLUMN id SET DEFAULT nextval('public.consentimentos_id_seq'::regclass);


--
-- Name: itens_pedido id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido ALTER COLUMN id SET DEFAULT nextval('public.itens_pedido_id_seq'::regclass);


--
-- Name: pedidos id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos ALTER COLUMN id SET DEFAULT nextval('public.pedidos_id_seq'::regclass);


--
-- Name: produto_imagens id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_imagens ALTER COLUMN id SET DEFAULT nextval('public.produto_imagens_id_seq'::regclass);


--
-- Name: produto_tamanhos id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_tamanhos ALTER COLUMN id SET DEFAULT nextval('public.produto_tamanhos_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


--
-- Data for Name: admins; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.admins (id, username, password, acesso, nome_completo) FROM stdin;
1	admin@loja.com	$argon2id$v=19$m=65536,t=3,p=4$5m5TTbABWq/vJrEgoUD53Q$eljGJ951UktV4QVjR5SlbImkBmkcn+fUl/IVTuOfzS0	admin	Administrador Jp Croco
\.


--
-- Data for Name: clientes; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.clientes (id, nome, email, telefone, created_at, cpf) FROM stdin;
2	Maria Eduarda da Costa Silva	ms.mariaeduarda6755@gmail.com	(61) 98174-1089	2026-09-02 14:07:56.449533	715.682.661-11
1	Mayckon Kennedy Santos Carvalho Duarte	mayckonkennedy877@gmail.com	(61) 98409-2729	2026-09-02 13:11:46.877032	712.071.951-38
\.


--
-- Data for Name: consentimentos; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.consentimentos (id, cliente_id, email, ip, versao, necessarios, analiticos, marketing, aceitou, criado_em) FROM stdin;
1	\N	teste@teste.com	\N	1.0	t	f	f	t	2026-09-02 17:26:33.345843
\.


--
-- Data for Name: itens_pedido; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.itens_pedido (id, pedido_id, produto_id, quantidade, preco_unitario, tamanho) FROM stdin;
1	1	1	1	0.00	P
5	8	2	1	1.00	M
6	9	2	1	1.00	M
7	10	2	1	1.00	M
8	11	2	1	1.00	M
9	12	2	1	1.00	M
10	15	2	1	1.00	M
11	16	2	1	1.00	G
12	17	2	1	1.00	G
13	18	2	1	0.50	G
14	19	2	1	0.50	G
15	20	2	2	0.50	G
\.


--
-- Data for Name: pedidos; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.pedidos (id, cliente_id, data_pedido, status, endereco_entrega, id_pedido, valor_total, codigo_rastreio, data_envio, transportadora, entrega_tipo) FROM stdin;
1	1	2026-09-02 13:11:46.9679	Enviado	Qe 40, 03 - 102, Guará - DF, CEP: 71070-062	OUZBTR	0.00	AB987654321CD	2026-09-02 14:22:41.80258	Correios	Correios
8	1	2026-09-02 19:43:20.784576	Entregue	Quadra QE 40 Conjunto F, 03 - Guara II, Brasília - DF, CEP: 71070-062	AETGYI	1.00	\N	\N	Correios	Uber Delivery
9	1	2026-09-02 20:04:29.298342	Entregue	Quadra QE 40 Conjunto F, 03 - Guara II, Brasília - DF, CEP: 71070-062	YHRHGN	1.00	\N	\N	Correios	Uber Delivery
12	1	2026-09-02 20:32:09.058382	Entregue	Quadra QE 40 Conjunto F, 03 - Guara II, Brasília - DF, CEP: 71070-062	CBCTEH	1.00	\N	\N	Correios	Uber Delivery
11	1	2026-09-02 20:18:47.636937	Entregue	Quadra QE 40 Conjunto F, 03 - Guara II, Brasília - DF, CEP: 71070-062	NAMJPQ	1.00	\N	\N	Correios	Uber Delivery
13	1	2026-09-02 20:35:27.22328	Entregue	QE 40 Teste PIX, Brasilia	TLGKNS	5.00	\N	\N	Correios	Retirada no local
14	1	2026-09-02 20:35:44.955657	Entregue	QE 40, 71070-062 Brasilia	TESTDF01	50.00	\N	\N	Correios	Retirada no local
15	1	2026-09-02 20:38:51.459289	Entregue	Quadra QE 40 Conjunto F, 03 - Guara II, Brasília - DF, CEP: 71070-062	WSXTDZ	1.00	\N	\N	Correios	Uber Delivery
10	1	2026-09-02 20:07:01.545163	Pago	Quadra QE 40 Conjunto F, 03 - Guará II, Brasília - DF, CEP: 71070-062	SYKLMQ	1.00	\N	\N	Correios	Uber Delivery
16	1	2026-09-02 21:29:56.323206	pendente	Guara II, 03 - Guara II, Brasília - DF, CEP: 71070-062	LMEWTS	1.00	\N	\N	Correios	Correios
17	1	2026-09-02 21:31:49.601914	pendente	Guara II, 03 - Guara II, Brasília - DF, CEP: 71070-062	BZIPMU	1.00	\N	\N	Correios	Correios
18	1	2026-09-02 21:37:00.036985	Pago	Qe 40, 03 - Guara II, Brasília - DF, CEP: 71070-062	BUQXEQ	0.50	\N	\N	Correios	Correios
19	1	2026-09-02 22:24:59.945698	pendente	Qe 40, 03 - Guara II, Brasília - DF, CEP: 71070-062	EYKDOH	0.50	\N	\N	Correios	Correios
20	1	2026-09-02 22:35:04.465404	pendente	Quadra QE 40 Conjunto F, 03 - apt 102, Brasília - DF, CEP: 71070-062	YAHMOH	1.00	\N	\N	Correios	Correios
\.


--
-- Data for Name: produto_imagens; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.produto_imagens (id, produto_id, url, ordem, criado_em) FROM stdin;
1	1	/uploads/7d7642d59d5c4747b67c9f511b5e83d0.jpg	0	2026-09-02 13:10:09.288878
6	2	/uploads/d729bfc022014c85832971a0aeeaf9ff.png	0	2026-09-02 21:36:07.671698
\.


--
-- Data for Name: produto_tamanhos; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.produto_tamanhos (id, produto_id, tamanho, stock, preco, criado_em) FROM stdin;
1	1	P	10	0.00	2026-09-02 13:10:09.272059
18	2	M	0	1.00	2026-09-02 21:36:07.626156
20	2	P	2	1.00	2026-09-02 21:36:07.645236
21	2	GG	4	1.00	2026-09-02 21:36:07.650885
19	2	G	3	1.00	2026-09-02 21:36:07.64
\.


--
-- Data for Name: produtos; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.produtos (id, nome, preco, tamanho, stock, ativo, created_at, imagem, preco_promocional, peso_gramas, comprimento, largura, altura, diametro, tp_objeto) FROM stdin;
1	Produto Teste	50.00	P	10	t	2026-09-02 13:10:09.249892	/uploads/7d7642d59d5c4747b67c9f511b5e83d0.jpg	\N	500	20	15	10	0	2
2	Lacoste Core Active	0.50	M	9	t	2026-09-02 19:31:03.264071	/uploads/d729bfc022014c85832971a0aeeaf9ff.png	\N	500	20	15	10	0	2
\.


--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.schema_migrations (version, applied_at) FROM stdin;
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: loja_admin
--

COPY public.usuarios (id, username, password, created_at, acesso, nome_completo) FROM stdin;
1	mayckonkennedy877@gmail.com	$argon2id$v=19$m=65536,t=3,p=4$Y6pC9zVW95i/tC88yfPASQ$tETJfSJbnW6EmF3OMu9trCwUVRpk5wOCAqx0XAMbKSw	2026-09-02 13:05:02.759145	usuario	Mayckon Kennedy Santos Carvalho Duarte
2	mayckonduarte006@gmail.com	$argon2id$v=19$m=65536,t=3,p=4$n+e/1FZx9bFbCT076gaSJA$2qvgzVEHCgK3PASZQP+d+W/gzzTQ+O/9VoPMHdN8sio	2026-09-02 14:22:27.417236	admin	Admin
\.


--
-- Name: admins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.admins_id_seq', 1, true);


--
-- Name: clientes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.clientes_id_seq', 3, true);


--
-- Name: consentimentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.consentimentos_id_seq', 1, true);


--
-- Name: itens_pedido_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.itens_pedido_id_seq', 15, true);


--
-- Name: pedidos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.pedidos_id_seq', 20, true);


--
-- Name: produto_imagens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.produto_imagens_id_seq', 6, true);


--
-- Name: produto_tamanhos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.produto_tamanhos_id_seq', 21, true);


--
-- Name: produtos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.produtos_id_seq', 2, true);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: loja_admin
--

SELECT pg_catalog.setval('public.usuarios_id_seq', 2, true);


--
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (id);


--
-- Name: admins admins_username_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_username_key UNIQUE (username);


--
-- Name: clientes clientes_cpf_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_cpf_key UNIQUE (cpf);


--
-- Name: clientes clientes_email_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_email_key UNIQUE (email);


--
-- Name: clientes clientes_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.clientes
    ADD CONSTRAINT clientes_pkey PRIMARY KEY (id);


--
-- Name: consentimentos consentimentos_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.consentimentos
    ADD CONSTRAINT consentimentos_pkey PRIMARY KEY (id);


--
-- Name: itens_pedido itens_pedido_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido
    ADD CONSTRAINT itens_pedido_pkey PRIMARY KEY (id);


--
-- Name: pedidos pedidos_id_pedido_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_id_pedido_key UNIQUE (id_pedido);


--
-- Name: pedidos pedidos_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_pkey PRIMARY KEY (id);


--
-- Name: produto_imagens produto_imagens_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_imagens
    ADD CONSTRAINT produto_imagens_pkey PRIMARY KEY (id);


--
-- Name: produto_tamanhos produto_tamanhos_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_tamanhos
    ADD CONSTRAINT produto_tamanhos_pkey PRIMARY KEY (id);


--
-- Name: produto_tamanhos produto_tamanhos_produto_id_tamanho_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_tamanhos
    ADD CONSTRAINT produto_tamanhos_produto_id_tamanho_key UNIQUE (produto_id, tamanho);


--
-- Name: produtos produtos_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produtos
    ADD CONSTRAINT produtos_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_username_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_username_key UNIQUE (username);


--
-- Name: idx_pedidos_codigo_rastreio; Type: INDEX; Schema: public; Owner: loja_admin
--

CREATE INDEX idx_pedidos_codigo_rastreio ON public.pedidos USING btree (codigo_rastreio);


--
-- Name: idx_pedidos_status; Type: INDEX; Schema: public; Owner: loja_admin
--

CREATE INDEX idx_pedidos_status ON public.pedidos USING btree (status);


--
-- Name: consentimentos consentimentos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.consentimentos
    ADD CONSTRAINT consentimentos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id) ON DELETE SET NULL;


--
-- Name: itens_pedido itens_pedido_pedido_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido
    ADD CONSTRAINT itens_pedido_pedido_id_fkey FOREIGN KEY (pedido_id) REFERENCES public.pedidos(id) ON DELETE CASCADE;


--
-- Name: itens_pedido itens_pedido_produto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido
    ADD CONSTRAINT itens_pedido_produto_id_fkey FOREIGN KEY (produto_id) REFERENCES public.produtos(id) ON DELETE RESTRICT;


--
-- Name: pedidos pedidos_cliente_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id) ON DELETE RESTRICT;


--
-- Name: produto_imagens produto_imagens_produto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_imagens
    ADD CONSTRAINT produto_imagens_produto_id_fkey FOREIGN KEY (produto_id) REFERENCES public.produtos(id) ON DELETE CASCADE;


--
-- Name: produto_tamanhos produto_tamanhos_produto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produto_tamanhos
    ADD CONSTRAINT produto_tamanhos_produto_id_fkey FOREIGN KEY (produto_id) REFERENCES public.produtos(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict AclpYKiLs5KJF6wponnGEEshNHod4382cWKE0c45pCzLW01JGJBlEIpvRhrJqbD

