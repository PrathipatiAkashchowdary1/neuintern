import { SITE } from './Seo'

export const organizationSchema = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: SITE.SITE_NAME,
  url: SITE.SITE_URL,
  logo: `${SITE.SITE_URL}/icon.png`,
  image: `${SITE.SITE_URL}/icon.png`,
  sameAs: [
    'https://www.linkedin.com/company/neuintern',
    'https://www.instagram.com/neuintern',
    'https://twitter.com/neuintern',
  ],
  description:
    'NeuIntern helps students build career-ready skills through 4-week internship programs in technology, AI, data, and cloud domains.',
}

export const websiteSchema = {
  '@context': 'https://schema.org',
  '@type': 'WebSite',
  name: SITE.SITE_NAME,
  url: SITE.SITE_URL,
  description:
    'NeuIntern offers practical 4-week internship programs with live projects, guided learning, and certificates for students.',
  inLanguage: 'en',
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
    image: program.image || `${SITE.SITE_URL}/icon.png`,
    provider: {
      '@type': 'Organization',
      name: SITE.SITE_NAME,
      sameAs: SITE.SITE_URL,
      logo: `${SITE.SITE_URL}/icon.png`,
    },
    educationalLevel: 'Beginner to Intermediate',
    teaches: Array.isArray(program.skills) ? program.skills : [],
    hasCourseInstance: {
      '@type': 'CourseInstance',
      courseMode: program.mode,
      courseWorkload: program.duration,
      inLanguage: 'en',
    },
  }
}
