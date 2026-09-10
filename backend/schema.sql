--
-- PostgreSQL database dump
--

\restrict 5LFuXVMaf6UOWb4roI68Y8A8xNh9bJabTMvBUS5wP8qv7vuydLQuJIgWH6U8Olj

-- Dumped from database version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

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
    acesso character varying(10) NOT NULL
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
-- Name: itens_pedido; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.itens_pedido (
    id integer NOT NULL,
    pedido_id integer NOT NULL,
    produto_id integer NOT NULL,
    quantidade integer NOT NULL,
    preco_unitario numeric(10,2) NOT NULL,
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
    numero_pedido character varying(50) NOT NULL,
    valor_total numeric(10,2) DEFAULT 0.00 NOT NULL
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
    CONSTRAINT produtos_preco_check CHECK ((preco >= (0)::numeric)),
    CONSTRAINT produtos_stock_check CHECK ((stock >= 0))
);


ALTER TABLE public.produtos OWNER TO loja_admin;

--
-- Name: produtos_id_seq; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

CREATE SEQUENCE public.produtos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.produtos_id_seq OWNER TO loja_admin;

--
-- Name: produtos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: loja_admin
--

ALTER SEQUENCE public.produtos_id_seq OWNED BY public.produtos.id;


--
-- Name: produtos_id_seq1; Type: SEQUENCE; Schema: public; Owner: loja_admin
--

ALTER TABLE public.produtos ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.produtos_id_seq1
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: loja_admin
--

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    username character varying(150) NOT NULL,
    password character varying(200) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    acesso character varying(10) NOT NULL
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
-- Name: itens_pedido id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido ALTER COLUMN id SET DEFAULT nextval('public.itens_pedido_id_seq'::regclass);


--
-- Name: pedidos id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos ALTER COLUMN id SET DEFAULT nextval('public.pedidos_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


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
-- Name: itens_pedido itens_pedido_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido
    ADD CONSTRAINT itens_pedido_pkey PRIMARY KEY (id);


--
-- Name: pedidos pedidos_numero_pedido_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_numero_pedido_key UNIQUE (numero_pedido);


--
-- Name: pedidos pedidos_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT pedidos_pkey PRIMARY KEY (id);


--
-- Name: produtos produtos_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.produtos
    ADD CONSTRAINT produtos_pkey PRIMARY KEY (id);


--
-- Name: usuarios usuarios_email_key; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_email_key UNIQUE (username);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: itens_pedido fk_itens_pedido_pedido; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido
    ADD CONSTRAINT fk_itens_pedido_pedido FOREIGN KEY (pedido_id) REFERENCES public.pedidos(id) ON DELETE CASCADE;


--
-- Name: itens_pedido fk_itens_pedido_produto; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.itens_pedido
    ADD CONSTRAINT fk_itens_pedido_produto FOREIGN KEY (produto_id) REFERENCES public.produtos(id) ON DELETE RESTRICT;


--
-- Name: pedidos fk_pedidos_cliente; Type: FK CONSTRAINT; Schema: public; Owner: loja_admin
--

ALTER TABLE ONLY public.pedidos
    ADD CONSTRAINT fk_pedidos_cliente FOREIGN KEY (cliente_id) REFERENCES public.clientes(id) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict 5LFuXVMaf6UOWb4roI68Y8A8xNh9bJabTMvBUS5wP8qv7vuydLQuJIgWH6U8Olj

