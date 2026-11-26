export function estimatePdfFilename(estimate) {
  const name = ['車禍估價單', estimate.id || '未儲存', estimate.license_plate || estimate.customer_name, estimate.estimate_date]
    .filter(Boolean).join('_').replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_');
  return `${name}.pdf`;
}

// Only accept the public print document, never the editor or the draft object.
export async function downloadAccidentEstimatePdf(publicDocument, filename, printStyles) {
  if (!publicDocument) throw new Error('請先開啟估價單預覽。');
  const source = publicDocument.cloneNode(true);
  const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas'), import('jspdf')]);
  const frame = document.createElement('iframe');
  frame.title = '車禍估價單 PDF';
  frame.setAttribute('aria-hidden', 'true');
  frame.style.cssText = 'position:fixed;left:-10000px;top:0;width:800px;height:1123px;border:0;';
  document.body.appendChild(frame);
  try {
    const doc = frame.contentDocument;
    doc.open();
    doc.write('<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><title>車禍估價單 PDF</title></head><body></body></html>');
    doc.close();
    const style = doc.createElement('style');
    style.textContent = `${printStyles}
      html, body { margin: 0; padding: 0; background: #fff; }
      .estimate-paper { width: 190mm; min-height: 0; margin: 0; padding: 0; }
      .pdf-page { width: 190mm; height: 277mm; overflow: hidden; background: #fff; }
    `;
    doc.head.appendChild(style);
    const original = source.querySelector('.estimate-paper');
    if (!original) throw new Error('找不到估價單內容，請重新開啟預覽。');
    const rows = [...original.querySelector('.estimate-paper-table tbody').rows];
    const totals = original.querySelector('.estimate-paper-totals');
    const footer = original.querySelector('.estimate-paper-footer');
    const template = original.cloneNode(true);
    template.querySelector('.estimate-paper-table tbody').replaceChildren();
    template.querySelector('.estimate-paper-totals')?.remove();
    template.querySelector('.estimate-paper-footer')?.remove();
    let page, paper, rowCount;
    const newPage = () => {
      page = doc.createElement('div');
      page.className = 'pdf-page';
      paper = template.cloneNode(true);
      page.appendChild(paper);
      doc.body.appendChild(page);
      rowCount = 0;
    };
    const fits = () => paper.getBoundingClientRect().height <= page.getBoundingClientRect().height - 1;
    newPage();
    await doc.fonts.ready;
    const append = (block, selector) => {
      const target = () => selector ? paper.querySelector(selector) : paper;
      target().appendChild(block);
      if (!fits()) {
        block.remove();
        if (!rowCount) throw new Error('估價單單一欄位內容過長，請縮短後再下載 PDF。');
        newPage();
        target().appendChild(block);
        if (!fits()) throw new Error('估價單單一欄位內容過長，請縮短後再下載 PDF。');
      }
      rowCount++;
    };
    // Paginate before rendering: large estimates never exceed a browser's canvas limit,
    // and item rows are kept intact with the headings repeated on each page.
    for (const row of rows) append(row.cloneNode(true), '.estimate-paper-table tbody');
    if (totals) append(totals.cloneNode(true), '.estimate-paper-table');
    if (footer) append(footer.cloneNode(true));
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait', compress: true });
    pdf.setProperties({ title: filename.replace(/\.pdf$/i, ''), creator: 'GFmotor' });
    for (let index = 0; index < doc.body.children.length; index++) {
      const current = doc.body.children[index];
      const canvas = await html2canvas(current, { scale: 2, backgroundColor: '#ffffff', logging: false });
      if (index) pdf.addPage();
      pdf.addImage(canvas, 'PNG', 10, 10, 190, 277);
      canvas.width = canvas.height = 0;
    }
    await pdf.save(filename, { returnPromise: true });
  } finally {
    frame.remove();
  }
}
