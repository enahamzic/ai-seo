'use client'
import { useEffect, useState } from 'react'
import styles from './article-shared.module.css'

function ArticleContent({ article }) {
  return (
    <main className={styles.page}>
      <article className={styles.article}>
        <header className={styles.header}>
          <h1 className={styles.title}>{article.title}</h1>
          <p className={styles.summary}>{article.summary}</p>
        </header>

        {article.sections.map((section) => (
          <section key={section.heading} className={styles.section}>
            <h2 className={styles.heading}>{section.heading}</h2>

            {section.paragraphs.map((paragraph, index) => (
              <p key={`${section.heading}-p-${index}`} className={styles.paragraph}>
                {paragraph}
              </p>
            ))}

            {Array.isArray(section.list) && section.list.length > 0 ? (
              <ul className={styles.list}>
                {section.list.map((item, index) => (
                  <li key={`${section.heading}-item-${index}`} className={styles.listItem}>
                    {item}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </article>
    </main>
  )
}

export default function CsrVersionPage() {
  const [article, setArticle] = useState(null)

  useEffect(() => {
    let isMounted = true

    async function loadArticle() {
      const response = await fetch('/api/get-article')
      const payload = await response.json()

      if (isMounted) {
        setArticle(payload.article)
      }
    }

    loadArticle()

    return () => {
      isMounted = false
    }
  }, [])

  if (!article) {
    return <div>Loading...</div>
  }

  return <ArticleContent article={article} />
}