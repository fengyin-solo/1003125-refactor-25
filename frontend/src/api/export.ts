/** 导出下载：所有模块页面共用的下载动作。
 *
 * 带上页面当前条件请求后端导出接口，把返回的 CSV 存成本地文件；
 * 同一批数据（地址和条件完全一致）的并发导出只放行最早那次请求，
 * 后续的原样拒绝，避免同一份清单被重复下载。
 */
import { request } from '@/api/client'

const inFlight = new Set<string>()

export async function downloadExport(endpoint: string, filters: Record<string, string>): Promise<void> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    const trimmed = value.trim()
    if (trimmed) {
      query.append(key, trimmed)
    }
  }
  const suffix = query.toString()
  const url = suffix ? `${endpoint}/export?${suffix}` : `${endpoint}/export`
  if (inFlight.has(url)) {
    throw new Error('相同条件的导出正在进行，等这次下载完成后再试')
  }
  inFlight.add(url)
  try {
    const response = await request(url)
    if (!response.ok) {
      throw new Error(`导出接口返回 ${response.status}，清单未生成`)
    }
    const blob = await response.blob()
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = resolveFilename(response.headers.get('Content-Disposition'), endpoint)
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(link.href)
  } finally {
    inFlight.delete(url)
  }
}

function resolveFilename(disposition: string | null, endpoint: string): string {
  const match = disposition?.match(/filename="?([^";]+)"?/)
  if (match?.[1]) {
    return match[1]
  }
  const module = endpoint.split('/').filter(Boolean).pop() ?? 'export'
  return `${module}-export.csv`
}
