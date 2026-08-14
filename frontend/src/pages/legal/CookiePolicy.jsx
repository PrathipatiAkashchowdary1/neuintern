import LegalPageLayout from './LegalPageLayout'

export default function CookiePolicy() {
  return (
    <LegalPageLayout title="Cookie Policy" path="/cookie-policy">
      <p>
  At NeuIntern, we believe in being transparent about how we collect and use data related to you. This Cookie Policy explains how and why we use cookies and similar tracking technologies when you visit our website. By continuing to browse or use our platform, you agree to our use of cookies as described in this policy to keep the website functional and to help us understand how it is used.
</p>

<h2>Types of cookies we use</h2>
<p>
  A cookie is a small text file saved on your computer or mobile device when you visit a website. We use these files to ensure our platform works efficiently and to gain insights into how visitors interact with our content. Specifically, we utilize the following categories of cookies:
</p>
<ul className="list-disc pl-5 space-y-1">
  <li><strong>Essential cookies</strong> — These are strictly necessary for the core functionality, security, and operation of our website. They enable you to navigate the platform, access secure areas, and ensure your sessions remain protected. Because these are critical to the site's basic operation, they cannot be disabled in our systems.</li>
  <li><strong>Analytics cookies</strong> — These cookies help us understand how users interact with our website by collecting and reporting aggregated, anonymous data. They track metrics such as page views, traffic sources, and the paths users take, which allows us to measure performance and continuously improve our website's user experience.</li>
</ul>

<h2>Managing cookies</h2>
<p>
  You have the right to decide whether to accept or reject non-essential cookies. You can manage your preferences and control or delete cookies directly through your web browser's settings menu. Most browsers allow you to clear existing cookies, block future cookies, or alert you when a cookie is being placed. Please be aware that if you choose to aggressively block or disable essential cookies, certain features of the NeuIntern website may not function properly, and your overall experience may be degraded.
</p>

<h2>Third-party cookies</h2>
<p>
  In some cases, we use third-party services to enhance your experience on our platform. Some embedded content, such as interactive maps, video players, or external application forms, is provided by third parties. When you interact with this integrated content, those external providers may set their own cookies on your device to track your engagement or personalize their services. NeuIntern does not control the placement of these third-party cookies, and their use is governed entirely by the privacy and cookie policies of the respective providers.
</p>
    </LegalPageLayout>
  )
}
