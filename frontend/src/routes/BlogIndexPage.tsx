import { Link } from '@tanstack/react-router'
import { SiteNavBrand, SitePublicMenu, BLOG_NAV } from '@/components/site/SiteNavBrand'
import { listBlogPosts } from '@/lib/blog/posts'
import './blog.scoped.css'

export function BlogIndexPage() {
  const posts = listBlogPosts()

  return (
    <div className="gs-blog">
      <div className="wrap">
        <header className="top">
          <a className="brand" href="/" aria-label="GymSite Intelligence">
            <SiteNavBrand />
          </a>
          <SitePublicMenu links={BLOG_NAV} activeHref="/blog" />
        </header>

        <section className="hero">
          <span className="eyebrow">Blog · inteligência de mercado</span>
          <h1>
            GymSite
            <span className="hl"> Intelligence</span>
          </h1>
          <p className="lede">
            Raio-X trimestral do setor de academias: aberturas, baixas, densidade e
            mortalidade — cidade a cidade, com base na Receita Federal.
          </p>
        </section>

        {posts.length === 0 ? (
          <p className="empty">Nenhum artigo publicado ainda.</p>
        ) : (
          <div className="list">
            {posts.map((p) => (
              <Link
                key={p.slug}
                to="/blog/$slug"
                params={{ slug: p.slug }}
                className="post-row"
              >
                <div>
                  <div className="meta">
                    {(
                      p.pills ?? [
                        p.angleLabel,
                        `${p.cityLabel}/${p.uf}`,
                        p.quarter.replace('-', ' · '),
                      ]
                    ).map((chip) => (
                      <span key={chip} className="chip">
                        {chip}
                      </span>
                    ))}
                  </div>
                  <h2>{p.title}</h2>
                  {p.excerpt ? <p className="ex">{p.excerpt}</p> : null}
                </div>
                <span className="go">Ler →</span>
              </Link>
            ))}
          </div>
        )}

        <footer className="foot">
          <a href="/">← GymSite Intelligence</a>
          {' · '}
          <a href="/privacidade">Privacidade</a>
        </footer>
      </div>
    </div>
  )
}
