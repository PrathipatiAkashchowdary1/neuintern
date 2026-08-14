import Seo from '../../seo/Seo'
import Breadcrumb from '../../components/common/Breadcrumb'

export default function LegalPageLayout({ title, path, updated = 'January 2026', children }) {
  return (
    <>
      <Seo title={title} path={path} noindex={false} description={`${title} for NeuIntern's internship platform.`} />
      <section className="pt-32 pb-24">
        <div className="container-page max-w-3xl">
          <Breadcrumb items={[{ name: 'Home', path: '/' }, { name: title, path }]} />
          <h1 className="text-4xl font-bold mt-8">{title}</h1>
          <p className="text-sm text-ink-400 mt-2">Last updated: {updated}</p>
          <div className="prose-legal mt-10 space-y-6 text-ink-800 leading-relaxed [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mt-10 [&_h2]:mb-3 [&_p]:text-ink-400 [&_li]:text-ink-400">
            {children}
          </div>
        </div>
      </section>
    </>
  )
}
