import Link from 'next/link'
import styles from './article-shared.module.css'

export default function HomePage() {
  return (
    <main className={styles.page}>
      <section className={styles.article}>
        <h1 className={styles.title}>Rendering Comparison Demo</h1>
        <p className={styles.summary}>
          Open either page below to compare server-rendered and client-rendered
          content delivery behavior.
        </p>

        <nav className={styles.navLinks}>
          <Link href="/ssr-version" className={styles.demoLink}>
            SSR Version
          </Link>
          <Link href="/csr-version" className={styles.demoLink}>
            CSR Version
          </Link>
        </nav>
      </section>
    </main>
  )
}