const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const Module = require('node:module');
const filename = path.resolve(__dirname, '../lib/brain-stream.ts');
const mod = new Module(filename, module);
mod.filename = filename;
mod.paths = module.paths;
mod._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText, filename);
const { readBrainStream } = mod.exports;
function stream(text, byteChunks = false) {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({ start(controller) {
    if (byteChunks) for (const byte of bytes) controller.enqueue(new Uint8Array([byte]));
    else controller.enqueue(bytes);
    controller.close();
  } });
}
test('fragmented UTF-8 and multiple JSON lines preserve answer and saved session ID', async () => {
  const events = [];
  await readBrainStream(stream('{"t":"init","session_id":7}\n{"t":"token","chunk":"中文回答"}\n{"t":"done"}', true), event => events.push(event));
  assert.equal(events[0].session_id, 7);
  assert.equal(events[1].chunk, '中文回答');
  assert.equal(events.at(-1).t, 'done');
});
test('provider error and premature EOF cannot produce successful completion', async () => {
  await assert.rejects(readBrainStream(stream('{"t":"token","chunk":"partial"}\n{"t":"error","msg":"模型失败"}\n'), () => {}), /模型失败/);
  await assert.rejects(readBrainStream(stream('{"t":"token","chunk":"partial"}\n'), () => {}), /中断/);
  await assert.rejects(readBrainStream(stream('{"t":"done"}\n'), () => {}), /中断/);
});
test('invalid JSON is rejected rather than silently dropping a result', async () => {
  await assert.rejects(readBrainStream(stream('{broken}\n'), () => {}), SyntaxError);
});
