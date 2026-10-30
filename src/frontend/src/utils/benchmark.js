const OBJECT_ID = /(?:^|[^0-9a-f])([0-9a-f]{24})(?![0-9a-f])/i;
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/i;

// Nhận link bài viết (…/posts/{id}, …/posts/slug/{slug}), ID 24 ký tự hoặc slug trần.
export function parsePostLink(input) {
  const text = String(input ?? '').trim();
  if (!text) return null;

  const id = text.match(OBJECT_ID)?.[1];
  if (id) return { id: id.toLowerCase() };

  let path = text;
  try {
    path = new URL(text, 'http://localhost').pathname;
  } catch {
    return null;
  }
  const last = path.split('/').filter(Boolean).pop() ?? '';
  let slug = last;
  try {
    slug = decodeURIComponent(last);
  } catch {
    return null;
  }
  return SLUG.test(slug) ? { slug: slug.toLowerCase() } : null;
}

function now() {
  return globalThis.performance?.now?.() ?? Date.now();
}

// Gửi `count` request tuần tự; tổng thời gian tính từ request đầu tới khi request cuối trả về.
export async function runBatch({ request, count, shouldStop, onProgress }) {
  const latencies = [];
  let hit = 0;
  let miss = 0;
  let errors = 0;
  const startedAt = now();

  for (let i = 0; i < count; i += 1) {
    if (shouldStop?.()) break;
    const t0 = now();
    try {
      const status = await request();
      if (status === 'HIT') hit += 1;
      else if (status === 'MISS') miss += 1;
    } catch {
      errors += 1;
    }
    latencies.push(now() - t0);
    onProgress?.({ done: i + 1, elapsedMs: now() - startedAt, latencies, hit, miss, errors });
  }

  return { count: latencies.length, totalMs: now() - startedAt, latencies: [...latencies], hit, miss, errors };
}

// Trung bình tổng thời gian qua các lần đo đã chạy xong của mỗi chế độ.
export function summarizeRounds(rounds) {
  const average = (mode) => {
    const totals = rounds.map((round) => round[mode]).filter((run) => run?.complete).map((run) => run.totalMs);
    return totals.length ? totals.reduce((sum, value) => sum + value, 0) / totals.length : null;
  };
  const redis = average('redis');
  const mongo = average('mongo');
  return {
    redisAvgMs: redis,
    mongoAvgMs: mongo,
    speedup: redis && mongo ? mongo / redis : null,
  };
}
