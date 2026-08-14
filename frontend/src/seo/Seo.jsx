import { Helmet } from 'react-helmet-async'

const SITE_NAME = 'NeuIntern'
const SITE_URL = 'https://www.neuintern.in'
const DEFAULT_IMAGE = `${SITE_URL}/og-image.jpg`

/**
 * Drop-in SEO tags for any route. Pass `structuredData` as a plain object
 * (or array of objects) and it will be serialized as JSON-LD.
 */
export default function Seo({
  title,
  description,
  path = '/',
  image = DEFAULT_IMAGE,
  keywords,
  structuredData,
  noindex = false,
}) {
  const fullTitle = title ? `${title} | ${SITE_NAME}` : `${SITE_NAME} — 4-Week Internship Programs`
  const canonical = `${SITE_URL}${path}`
  const desc =
    description ||
    'NeuIntern offers focused 4-week internship programs in web development, AI, data science, cloud, and more — real projects, real certificates.'

  const schemas = Array.isArray(structuredData) ? structuredData : structuredData ? [structuredData] : []

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={desc} />
      {keywords && <meta name="keywords" content={keywords} />}
      <link rel="canonical" href={canonical} />
      {noindex && <meta name="robots" content="noindex, nofollow" />}

      {/* Open Graph */}
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={desc} />
      <meta property="og:url" content={canonical} />
      <meta property="og:image" content={image} />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={desc} />
      <meta name="twitter:image" content={image} />

      {schemas.map((schema, i) => (
        <script key={i} type="application/ld+json">
          {JSON.stringify(schema)}
        </script>
      ))}
    </Helmet>
  )
}

export const SITE = { SITE_NAME, SITE_URL, DEFAULT_IMAGE }
