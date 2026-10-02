export type BrainSource = { doc_id: number; doc_name: string; kb_name?: string; content_preview?: string };
export type BrainEvent = { t: string; session_id?: number; msg?: string; chunk?: string; sources?: BrainSource[] };

/** Network chunks need not end at a JSON line or UTF-8 character. */
export async function readBrainStream(body: ReadableStream<Uint8Array>, onEvent: (event: BrainEvent) => void) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let doneReceived = false;
  let answer = '';
  function consume(line: string) {
    if (!line.trim()) return;
    const event: BrainEvent = JSON.parse(line);
    if (event.t === 'error') throw new Error(event.msg || '回答生成失败');
    if (event.t === 'token') answer += event.chunk || '';
    if (event.t === 'done') doneReceived = true;
    onEvent(event);
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      lines.forEach(consume);
      if (done) break;
    }
    consume(buffer);
    if (!doneReceived || !answer.trim()) throw new Error('回答中断，尚未确认保存，请重试');
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
