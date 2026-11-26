import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import { estimatePdfFilename } from '../src/utils/accidentEstimatePdf.js';

test('PDF names identify the estimate and remove filesystem separators', () => {
  assert.equal(estimatePdfFilename({ id: 12, license_plate: 'ABC-1234', estimate_date: '2026-11-26' }),
    '車禍估價單_12_ABC-1234_2026-11-26.pdf');
  assert.equal(estimatePdfFilename({ customer_name: '測試/客戶:一', estimate_date: '2026-11-26' }),
    '車禍估價單_未儲存_測試_客戶_一_2026-11-26.pdf');
});

const source = readFileSync(new URL('../src/views/admin/AccidentEstimates.vue', import.meta.url), 'utf8');
function harness(download) {
  const context = vm.createContext({
    ref: value => ({ value }), computed: get => ({ get value() { return get(); } }),
    useSiteStore: () => ({}), useAuthStore: () => ({}), hasPermission: () => true,
    watch() {}, onMounted() {}, onBeforeUnmount() {}, onBeforeRouteLeave() {},
    downloadAccidentEstimatePdf: download, estimatePdfFilename, printStyles: 'public-print-css',
  });
  const script = source.match(/<script setup>([\s\S]*?)<\/script>/)[1].replace(/^import .*;$/gm, '');
  vm.runInContext(script + `
    draft.value = { id: 7, customer_name: '測試', internal_note: 'PRIVATE_NOTE' };
    printDocument.value = { publicOnly: true };
    globalThis.state = { draft, printDocument, exportingPdf, pdfError };
  `, context);
  return context;
}

test('PDF download receives only the public document and never saves the draft', async () => {
  const calls = [];
  const h = harness(async (...args) => calls.push(args));
  await h.downloadPdf();
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], h.state.printDocument.value);
  assert.notEqual(calls[0][0], h.state.draft.value);
  assert.equal(calls[0][1], '車禍估價單_7_測試.pdf');
  assert.equal(h.state.exportingPdf.value, false);
});

test('repeated clicks are ignored during download and failures allow retry', async () => {
  let rejectDownload;
  let calls = 0;
  const h = harness(() => { calls++; return new Promise((resolve, reject) => { rejectDownload = reject; }); });
  const first = h.downloadPdf();
  await h.downloadPdf();
  assert.equal(calls, 1);
  assert.equal(h.state.exportingPdf.value, true);
  rejectDownload(new Error('下載測試失敗'));
  await first;
  assert.equal(h.state.exportingPdf.value, false);
  assert.equal(h.state.pdfError.value, '下載測試失敗');
  const retry = h.downloadPdf();
  assert.equal(calls, 2);
  rejectDownload(new Error('重試測試'));
  await retry;
});
