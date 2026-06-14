/**
 * PrivacidadePage — política de privacidade pública (acessível sem login).
 *
 * Estrutura adaptada da política da Geofusion/Cortex Intelligence
 * (https://geofusion.com.br/politica-de-privacidade/), reescrita para o
 * GymSite Intelligence: produto B2B de viabilidade de pontos comerciais
 * para academias de ginástica.
 *
 * Disclaimer: este texto é um rascunho técnico para o MVP — antes do
 * lançamento comercial, deve ser validado por advogado especializado
 * em LGPD.
 */
import { Link } from '@tanstack/react-router'

export function PrivacidadePage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="container flex h-14 items-center gap-6">
          <Link
            to="/login"
            className="flex items-center gap-2 font-semibold tracking-tight"
          >
            <span aria-hidden className="text-xl"></span>
            <span>GymSite Intelligence</span>
          </Link>
        </div>
      </header>

      <main className="container max-w-3xl py-10 space-y-6 text-sm leading-relaxed">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            Política de Privacidade
          </h1>
          <p className="text-muted-foreground">
            Última atualização: 12 de maio de 2026
          </p>
        </div>

        <Section title="1. Introdução">
          <p>
            O GymSite Intelligence é um produto operado por <strong>Vectra
            Cargo</strong> (CNPJ 59.650.913/0001-04). Esta política descreve
            como coletamos, usamos, armazenamos e compartilhamos dados
            pessoais durante o uso da plataforma de análise de viabilidade
            de pontos comerciais para academias.
          </p>
          <p>
            Operamos em conformidade com a Lei nº 13.709/2018
            (Lei Geral de Proteção de Dados — LGPD).
          </p>
        </Section>

        <Section title="2. Dados que coletamos">
          <p>Coletamos três categorias de dados:</p>
          <h3 className="font-semibold mt-3">2.1 Dados de cadastro</h3>
          <p>
            Email profissional fornecido no convite ou no login por Magic
            Link. Esse email é o identificador da sua conta na plataforma.
          </p>
          <h3 className="font-semibold mt-3">2.2 Dados de uso</h3>
          <p>
            Parâmetros que você informa em cada relatório (cidade, bairro,
            público-alvo, área desejada, tipo de negócio, exigências
            específicas), bem como timestamps de execução, status do
            pipeline e custo computacional.
          </p>
          <h3 className="font-semibold mt-3">2.3 Dados técnicos</h3>
          <p>
            Endereço IP, tipo de dispositivo, navegador e logs de erro,
            coletados apenas para garantir disponibilidade e diagnosticar
            problemas técnicos.
          </p>
        </Section>

        <Section title="3. Finalidades do tratamento">
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Operação do serviço:</strong> executar o pipeline de
              análise (Google Maps, IBGE, classificação semântica) com base
              nos parâmetros que você informa.
            </li>
            <li>
              <strong>Persistência:</strong> armazenar os relatórios
              gerados na sua organização, permitindo consulta posterior.
            </li>
            <li>
              <strong>Autenticação e segurança:</strong> validar identidade
              via Magic Link, prevenir acesso indevido, registrar eventos
              de auditoria.
            </li>
            <li>
              <strong>Melhoria do produto:</strong> métricas agregadas e
              anônimas para evolução das heurísticas e do modelo de scoring.
            </li>
          </ul>
        </Section>

        <Section title="4. Base legal (LGPD)">
          <p>
            Tratamos dados pessoais com base em:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Execução de contrato</strong> (art. 7º, V) — operar
              o serviço contratado.
            </li>
            <li>
              <strong>Legítimo interesse</strong> (art. 7º, IX) — segurança,
              prevenção a fraude, melhoria de produto.
            </li>
            <li>
              <strong>Cumprimento de obrigação legal</strong> (art. 7º, II)
              — quando aplicável.
            </li>
          </ul>
        </Section>

        <Section title="5. Compartilhamento de dados">
          <p>
            Para operar o produto, dados podem ser transmitidos aos
            seguintes processadores:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>
              <strong>Supabase</strong> (armazenamento e autenticação) —
              servidores localizados nos EUA, sob cláusulas-padrão.
            </li>
            <li>
              <strong>Google Cloud</strong> (Maps Places API, Gemini API,
              Geocoding) — para enriquecimento dos relatórios.
            </li>
            <li>
              <strong>Provedor de email transacional</strong> — entrega do
              Magic Link de login.
            </li>
          </ul>
          <p>
            Não vendemos dados pessoais a terceiros. Não compartilhamos
            dados com fins de marketing externo.
          </p>
        </Section>

        <Section title="6. Retenção">
          <p>
            Relatórios e dados de cadastro são mantidos enquanto sua conta
            estiver ativa. Após solicitação de exclusão, removemos os
            dados em até 30 dias, ressalvados aqueles que devamos manter
            por obrigação legal (até 5 anos para fins fiscais ou de
            auditoria, conforme art. 16 da LGPD).
          </p>
        </Section>

        <Section title="7. Segurança">
          <p>
            Adotamos medidas técnicas e administrativas para proteger seus
            dados: criptografia em trânsito (TLS), criptografia em repouso
            no Supabase, controle de acesso por organização via Row Level
            Security (RLS), logs de auditoria e princípio do mínimo
            privilégio para a equipe interna.
          </p>
        </Section>

        <Section title="8. Direitos do titular (LGPD art. 18)">
          <p>Você pode, a qualquer momento, exercer os direitos de:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Confirmação da existência de tratamento</li>
            <li>Acesso aos dados</li>
            <li>Correção de dados incompletos, inexatos ou desatualizados</li>
            <li>Anonimização, bloqueio ou eliminação de dados</li>
            <li>Portabilidade dos dados</li>
            <li>Eliminação dos dados tratados com consentimento</li>
            <li>Informação sobre compartilhamento</li>
            <li>Revogação do consentimento</li>
          </ul>
          <p>
            Para exercer qualquer direito, escreva para o Encarregado de
            Dados (DPO) — contato na seção 11.
          </p>
        </Section>

        <Section title="9. Cookies">
          <p>
            Utilizamos cookies essenciais ao funcionamento (sessão
            autenticada, preferências de organização). Não usamos cookies
            de marketing nem de rastreamento por terceiros.
          </p>
        </Section>

        <Section title="10. Transferência internacional">
          <p>
            Como utilizamos infraestrutura em nuvem, alguns dados podem
            ser processados ou armazenados em servidores localizados fora
            do Brasil (Estados Unidos). Essas transferências obedecem ao
            art. 33 da LGPD, observadas cláusulas-padrão e nível adequado
            de proteção.
          </p>
        </Section>

        <Section title="11. Contato — Encarregado de Dados (DPO)">
          <p>
            Para qualquer questão relativa a tratamento de dados pessoais,
            entre em contato:
          </p>
          <p>
            <strong>Email:</strong>{' '}
            <a
              href="mailto:dpo@vectracargo.com.br"
              className="underline hover:text-foreground"
            >
              dpo@vectracargo.com.br
            </a>
          </p>
        </Section>

        <Section title="12. Alterações nesta política">
          <p>
            Esta política pode ser atualizada para refletir mudanças
            legais, regulatórias ou do próprio serviço. A versão vigente
            estará sempre disponível nesta URL, com data de última
            atualização no topo.
          </p>
        </Section>

        <div className="pt-6 border-t border-border">
          <Link
            to="/login"
            className="text-sm text-muted-foreground hover:text-foreground underline"
          >
            ← Voltar para o login
          </Link>
        </div>
      </main>
    </div>
  )
}

function Section({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <div className="space-y-2 text-muted-foreground">{children}</div>
    </section>
  )
}
