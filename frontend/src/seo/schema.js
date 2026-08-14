import { SITE } from './Seo'

export const organizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: SITE.SITE_NAME,
  url: SITE.SITE_URL,
  logo: `${SITE.SITE_URL}/logo.png`,
  sameAs: [
    'https://www.linkedin.com/company/neuintern',
    'https://www.instagram.com/neuintern',
    'https://twitter.com/neuintern',
  ],
}

export const websiteSchema = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: SITE.SITE_NAME,
  url: SITE.SITE_URL,
  potentialAction: {
    '@type': 'SearchAction',
    target: `${SITE.SITE_URL}/programs?search={search_term_string}`,
    'query-input': 'required name=search_term_string',
  },
}

export function breadcrumbSchema(items) {
  // items: [{ name, path }]
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: `${SITE.SITE_URL}${item.path}`,
    })),
  }
}

export function courseSchema(program) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Course',
    name: program.title,
    description: program.tagline,
    provider: {
      '@type': 'Organization',
      name: SITE.SITE_NAME,
      sameAs: SITE.SITE_URL,
    },
    hasCourseInstance: {
      '@type': 'CourseInstance',
      courseMode: program.mode,
      courseWorkload: program.duration,
    },
  }
}
