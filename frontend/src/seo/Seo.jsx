import { Helmet } from 'react-helmet-async'

const SITE_NAME = 'NeuIntern'
// The public address. It must match the sitemap, robots.txt, index.html and the www -> apex
// redirect in public/.htaccess, otherwise every page names a canonical URL that redirects.
const SITE_URL = 'https://neuintern.in'
const DEFAULT_IMAGE = `${SITE_URL}/icon.png`

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
    'NeuIntern offers focused 4-week internship programs in web development, AI, data science, cloud, cyber security, and more — real projects, real certificates.'

  const schemas = Array.isArray(structuredData) ? structuredData : structuredData ? [structuredData] : []

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={desc} />
      <meta name="robots" content={noindex ? 'noindex, nofollow' : 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'} />
      <meta name="author" content={SITE_NAME} />
      <meta name="language" content="en" />
      {keywords && <meta name="keywords" content={keywords} />}
      <link rel="canonical" href={canonical} />
      <link rel="alternate" hrefLang="en" href={canonical} />

      {/* Open Graph */}
      <meta property="og:type" content="website" />
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:locale" content="en_US" />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={desc} />
      <meta property="og:url" content={canonical} />
      <meta property="og:image" content={image} />
      <meta property="og:image:alt" content={fullTitle} />

      {/* Twitter */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content="@neuintern" />
      <meta name="twitter:creator" content="@neuintern" />
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
