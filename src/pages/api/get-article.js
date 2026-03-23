import { readFile } from 'node:fs/promises'
import path from 'node:path'

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', ['GET'])
    return res.status(405).json({ error: 'Method Not Allowed' })
  }

  try {
    const filePath = path.join(process.cwd(), 'data', 'articles.json')
    const fileContents = await readFile(filePath, 'utf8')
    const payload = JSON.parse(fileContents)

    return res.status(200).json(payload)
  } catch (error) {
    return res.status(500).json({ error: 'Failed to load article data' })
  }
}