import { Link, Navigate, useParams } from '@tanstack/react-router'
import {
  AgeBandBars,
  KpiGrid,
  LeadMagnet,
  PillRow,
  SeriesCompare,
  SourceSeal,
  StickyToc,
} from '@/components/blog/DossierParts'
import { ReadingProgress } from '@/components/blog/ReadingProgress'
import { getBlogPost, getRelatedPosts } from '@/lib/blog/posts'
import './blog.scoped.css'

export function BlogSlugPage() {
  const { slug } = useParams({ from: '/blog/$slug' })
  const post = getBlogPost(slug)
  if (!post) return <Navigate to="/blog" replace />
  const related = getRelatedPosts(slug, 3)
  const showAgeInFlow = post.bodyHtml.includes('<!--AGE_BANDS-->')
  const bodyParts = showAgeInFlow
    ? post.bodyHtml.split('<!--AGE_BANDS-->')
    : [post.bodyHtml]

  return (
    <div className="gs-blog is-dossier">
      <ReadingProgress targetSelector=".dossier-scroll" />

      <div className="wrap">
        <header className="top">
          <a className="brand" href="/">
            <img src="/gymsite-logo-white.png" alt="GymSite Intelligence" />
          </a>
          <nav className="nav">
            <a href="/#fontes">Fontes</a>
            <a href="/agentes">Especialistas</a>
            <a href="/explorar">Explorar</a>
            <Link to="/blog" className="is-active">
              Blog
            </Link>
            <a href="/degustacao">Degustação</a>
          </nav>
        </header>
      </div>

      <div className="dossier-shell wrap">
        <aside className="dossier-side">
          <StickyToc items={post.toc} />
        </aside>

        <div className="dossier-main dossier-scroll">
          <div className="article-hero">
            <Link to="/blog" className="back">
              ← Todos os artigos
            </Link>
            <PillRow pills={post.pills} />
            <p className="city-kicker">
              {post.cityLabel}/{post.uf} · {post.angleLabel}
            </p>
            <h1>{post.title}</h1>
            <KpiGrid kpis={post.kpis} />
            <SourceSeal sources={post.sourceSeal} />
          </div>

          <article className="prose">
            {bodyParts.map((chunk, idx) => (
              <div key={idx}>
                <div dangerouslySetInnerHTML={{ __html: chunk }} />
                {showAgeInFlow && idx === 0 && post.ageBands.length > 0 ? (
                  <AgeBandBars bands={post.ageBands} title={post.ageBandsTitle} />
                ) : null}
              </div>
            ))}
            {!showAgeInFlow && post.ageBands.length > 0 ? (
              <AgeBandBars bands={post.ageBands} title={post.ageBandsTitle} />
            ) : null}
          </article>

          <LeadMagnet cityLabel={post.cityLabel} uf={post.uf} />
          <SeriesCompare cityLabel={post.cityLabel} related={related} />

          <div className="cta">
            <div>
              <h3>Raio-X da sua região, com dados</h3>
              <p>
                Cruze saturação, demanda e concorrência antes de assinar o contrato —
                degustação GymSite, sem lock-in.
              </p>
            </div>
            <a className="btn" href="/degustacao">
              Começar degustação
            </a>
          </div>

          <footer className="foot">
            <Link to="/blog">← Blog</Link>
            {' · '}
            <a href="/">GymSite Intelligence</a>
          </footer>
        </div>
      </div>
    </div>
  )
}
