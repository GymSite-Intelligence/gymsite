-- =============================================================================
-- Sincronização GymSite → VectraClip (prospect_profiles)
-- Aplica no SQL Editor do Supabase: https://supabase.com/dashboard/project/_/sql
-- =============================================================================

-- 1. Função que mapeia oportunidades_prospeccao → prospect_profiles
CREATE OR REPLACE FUNCTION sync_gymsite_oportunidade_to_prospect()
RETURNS TRIGGER AS $$
DECLARE
    v_company_id uuid;
    v_decisor jsonb;
    v_endereco jsonb;
    v_dados_publicos jsonb;
BEGIN
    -- ignora se não é status de webhook enviado
    IF NEW.status IS DISTINCT FROM 'webhook_enviado' THEN
        RETURN NEW;
    END IF;

    -- evita duplicata: já existe prospect para este CNPJ?
    IF EXISTS (
        SELECT 1 FROM prospect_profiles
        WHERE cnpj = NEW.cnpj
        LIMIT 1
    ) THEN
        RETURN NEW;
    END IF;

    -- busca company_id fixo (ou configure conforme seu tenant)
    -- NOTE: ajuste este UUID para o company_id correto do seu tenant
    v_company_id := '00000000-0000-0000-0000-000000000001'::uuid;

    -- monta objeto decisor
    v_decisor := jsonb_build_object(
        'nome', COALESCE(NEW.contato_cnpj->>'decision_maker', ''),
        'cargo', COALESCE(NEW.contato_cnpj->>'cargo', ''),
        'email', COALESCE(NEW.contato_cnpj->>'email', ''),
        'whatsapp', COALESCE(NEW.contato_cnpj->>'whatsapp', ''),
        'linkedin', COALESCE(NEW.contato_cnpj->>'linkedin', '')
    );

    -- monta endereco
    v_endereco := jsonb_build_object(
        'logradouro', COALESCE(NEW.endereco_cnpj->>'logradouro', ''),
        'numero', COALESCE(NEW.endereco_cnpj->>'numero', ''),
        'bairro', COALESCE(NEW.endereco_cnpj->>'bairro', ''),
        'cidade', NEW.cidade,
        'uf', NEW.uf,
        'cep', COALESCE(NEW.endereco_cnpj->>'cep', '')
    );

    -- monta dados_publicos com info da obra
    v_dados_publicos := jsonb_build_object(
        'nome_obra', NEW.nome_obra,
        'situacao_obra', NEW.situacao_obra,
        'area_total_m2', NEW.area_total_m2,
        'data_inicio_obra', NEW.data_inicio_obra,
        'data_situacao_obra', NEW.data_situacao_obra,
        'cno', NEW.cno,
        'segmento_operacao', NEW.segmento_operacao,
        'score_match', NEW.score_match,
        'motivo_match', NEW.motivo_match,
        'prioridade', NEW.prioridade,
        'origem', 'gymsite_auto'
    );

    -- insere na tabela do VectraClip
    INSERT INTO prospect_profiles (
        company_id,
        nome_razao_social,
        cnpj,
        setor,
        cidade,
        uf,
        endereco,
        telefone,
        email_contato,
        decisores,
        dados_publicos,
        status,
        temperatura,
        score,
        origem,
        created_at,
        updated_at
    ) VALUES (
        v_company_id,
        COALESCE(NEW.razao_social, NEW.nome_fantasia, ''),
        NEW.cnpj,
        NEW.segmento_operacao,
        NEW.cidade,
        NEW.uf,
        v_endereco,
        COALESCE(NEW.contato_cnpj->>'telefone', ''),
        COALESCE(NEW.contato_cnpj->>'email', ''),
        CASE WHEN v_decisor->>'nome' <> '' THEN jsonb_build_array(v_decisor) ELSE '[]'::jsonb END,
        v_dados_publicos,
        'COLD',           -- status inicial no pipeline Vectra
        'frio',           -- temperatura
        COALESCE(NEW.score_match, 0)::int,
        'gymsite_auto',
        NOW(),
        NOW()
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Trigger que dispara quando status muda para 'webhook_enviado'
DROP TRIGGER IF EXISTS trg_sync_gymsite_to_prospect ON oportunidades_prospeccao;

CREATE TRIGGER trg_sync_gymsite_to_prospect
    AFTER INSERT OR UPDATE OF status ON oportunidades_prospeccao
    FOR EACH ROW
    WHEN (NEW.status = 'webhook_enviado')
    EXECUTE FUNCTION sync_gymsite_oportunidade_to_prospect();

-- =============================================================================
-- Teste manual (opcional):
-- =============================================================================
-- UPDATE oportunidades_prospeccao SET status = 'webhook_enviado'
-- WHERE id = '<uuid-de-uma-oportunidade>';
--
-- SELECT * FROM prospect_profiles WHERE origem = 'gymsite_auto';
