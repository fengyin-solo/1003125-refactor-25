/** 导出下载的共用方法：各模块页面不再各自拼地址、调 window.open。
 *
 * 带上页面当前条件请求后端导出接口，把响应存成文件；
 * 查询串的拼法与列表请求保持一致，保证导出和列表是同一份取数口径。
 */
import { request } from '@/api/client'

// 正在进行中的导出，key 为「地址+条件」：同一批数据只认最早那次请求
const pendingExports = new Set<string>()

function exportFilename(response: Response, endpoint: string): string {
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const match = /filename="?([^";]+)"?/.exec(disposition)
  if (match) {
    return match[1]
  }
  const module = endpoint.split('/').filter(Boolean).pop() ?? 'export'
  return `${module}-export.csv`
}

export async function downloadExport(endpoint: string, filters: Record<string, string>): Promise<void> {
  const query = new URLSearchParams(filters).toString()
  const url = query ? `${endpoint}/export?${query}` : `${endpoint}/export`
  if (pendingExports.has(url)) {
    throw new Error('相同条件的导出正在进行，等这次完成后再试')
  }
  pendingExports.add(url)
  try {
    const response = await request(url)
    if (!response.ok) {
      throw new Error(`导出接口返回 ${response.status}，清单未生成`)
    }
    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = objectUrl
    link.download = exportFilename(response, endpoint)
    link.click()
    URL.revokeObjectURL(objectUrl)
  } finally {
    pendingExports.delete(url)
  }
}
