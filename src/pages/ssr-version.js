import { readFile } from 'node:fs/promises'
import path from 'node:path'
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

export async function getServerSideProps() {
  const filePath = path.join(process.cwd(), 'data', 'articles.json')
  const fileContents = await readFile(filePath, 'utf8')
  const payload = JSON.parse(fileContents)

  return {
    props: {
      article: payload.article,
    },
  }
}

export default function SsrVersionPage({ article }) {
  return <ArticleContent article={article} />
}