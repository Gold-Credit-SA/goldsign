-- ============================================================
-- MIGRATION: posição da assinatura visível por solicitação
-- Execute no SQL Editor do Supabase para ambientes já existentes.
-- ============================================================

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_pagina INTEGER NOT NULL DEFAULT 1;

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_x NUMERIC(6,5) NOT NULL DEFAULT 0.06;

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_y NUMERIC(6,5) NOT NULL DEFAULT 0.06;

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_largura NUMERIC(6,5) NOT NULL DEFAULT 0.44;

ALTER TABLE solicitacoes_assinatura
    ADD COLUMN IF NOT EXISTS assinatura_altura NUMERIC(6,5) NOT NULL DEFAULT 0.12;

-- Constraints de faixa (0..1)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_solicitacoes_assinatura_x_range'
    ) THEN
        ALTER TABLE solicitacoes_assinatura
            ADD CONSTRAINT ck_solicitacoes_assinatura_x_range
            CHECK (assinatura_x >= 0 AND assinatura_x <= 1);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_solicitacoes_assinatura_y_range'
    ) THEN
        ALTER TABLE solicitacoes_assinatura
            ADD CONSTRAINT ck_solicitacoes_assinatura_y_range
            CHECK (assinatura_y >= 0 AND assinatura_y <= 1);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_solicitacoes_assinatura_largura_range'
    ) THEN
        ALTER TABLE solicitacoes_assinatura
            ADD CONSTRAINT ck_solicitacoes_assinatura_largura_range
            CHECK (assinatura_largura > 0 AND assinatura_largura <= 1);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'ck_solicitacoes_assinatura_altura_range'
    ) THEN
        ALTER TABLE solicitacoes_assinatura
            ADD CONSTRAINT ck_solicitacoes_assinatura_altura_range
            CHECK (assinatura_altura > 0 AND assinatura_altura <= 1);
    END IF;
END $$;

