const fs = require('fs');
const d = require('docx');
const { Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, AlignmentType, HeadingLevel, LevelFormat,
  ImageRun, Footer, Header, PageNumber, TabStopType, LeaderType } = d;

const W = 9922;                       // ancho útil: A4 con márgenes izquierdo 1134 y derecho 851
const BODY = 'Georgia', SANS = 'Arial', MONO = 'Consolas';
const GRIS1 = 'F2F2F2', GRIS2 = 'D9D9D9', ROJO = 'FF0000', AVISO = 'FFF3EE';
const white = { style: BorderStyle.SINGLE, size: 4, color: 'FFFFFF' };
const wb = { top: white, bottom: white, left: white, right: white };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };

class Builder {
  constructor(opt) {
    this.opt = opt; this.kids = []; this.heads = []; this.h1n = 0; this.h2n = 0; this.nt = 0; this.nf = 0; this.ne = 0;
    this.refs = {}; this.refsOut = {}; this.pages = {}; this.nol = 0; this.tocIndex = null;
    if (process.env.PAGES && fs.existsSync(process.env.PAGES)) this.pages = JSON.parse(fs.readFileSync(process.env.PAGES));
    if (process.env.REFS && fs.existsSync(process.env.REFS)) this.refs = JSON.parse(fs.readFileSync(process.env.REFS));
  }
  push(...x) { this.kids.push(...x); }
  gap(n = 120) { return new Paragraph({ spacing: { after: n, line: 240, lineRule: 'auto' }, children: [] }); }
  resolve(t) {
    return String(t).replace(/\{([STFE]):(\w+)\}/g, (m, k, key) => {
      const v = this.refs[k + ':' + key];
      if (!v) { if (process.env.REFS) console.error('REF SIN RESOLVER', m); return '?'; }
      return k === 'T' ? 'Tabla ' + v : k === 'F' ? 'Figura ' + v : k === 'E' ? '(' + v + ')' : v;
    });
  }
  runs(text, o = {}) {
    text = this.resolve(text);
    if (text.includes('—')) console.error('RAYA LARGA:', text.slice(0, 80));
    const out = [];
    for (const s of text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*\s][^*]*\*)/)) {
      if (!s) continue;
      const base = { font: o.font || BODY, size: o.size, color: o.color };
      if (s.startsWith('**')) out.push(new TextRun({ ...base, text: s.slice(2, -2), bold: true }));
      else if (s.startsWith('`')) out.push(new TextRun({ text: s.slice(1, -1), font: MONO, size: (o.size || 22) - 3, color: o.color }));
      else if (s.startsWith('*') && s.length > 2) out.push(new TextRun({ ...base, text: s.slice(1, -1), italics: true, bold: o.bold }));
      else out.push(new TextRun({ ...base, text: s, bold: o.bold, italics: o.italics }));
    }
    return out;
  }
  // ----- portada
  title(titulo, version, filas) {
    this.push(new Paragraph({ spacing: { after: 120, line: 320, lineRule: 'exact' }, children: [new TextRun({ text: titulo, font: SANS, size: 32, color: ROJO })] }));
    this.push(new Paragraph({ spacing: { after: 360 }, children: [new TextRun({ text: version, font: BODY, bold: true, size: 22 })] }));
    const w1 = 1300, w2 = W - w1;
    this.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [w1, w2], rows: filas.map(([k, v]) => new TableRow({ children: [
      this.cell(k, w1, { fill: GRIS2, bold: true }), this.cell(v, w2, { fill: GRIS1 })] })) }));
    this.push(this.gap(240));
  }
  cell(text, w, o = {}) {
    const paras = (Array.isArray(text) ? text : [text]).map(t => new Paragraph({ keepNext: o.head, alignment: o.align || (o.head ? AlignmentType.CENTER : AlignmentType.LEFT),
      spacing: { before: 20, after: 20, line: 240, lineRule: 'auto' }, children: this.runs(t, { size: 18, bold: o.head || o.bold }) }));
    return new TableCell({ width: { size: w, type: WidthType.DXA }, borders: wb, verticalAlign: d.VerticalAlign.CENTER, margins: { top: 30, bottom: 30, left: 85, right: 85 },
      shading: { fill: o.fill || GRIS1, type: ShadingType.CLEAR, color: 'auto' }, children: paras });
  }
  // ----- títulos
  h2u(t, brk = false) { this.push(new Paragraph({ heading: HeadingLevel.HEADING_2, pageBreakBefore: brk, spacing: { before: 200, after: 200 }, children: [new TextRun({ text: t, font: BODY, bold: true, size: 24 })] })); }
  h1(key, t) {
    this.h1n++; this.h2n = 0; const n = this.h1n + '.';
    this.refsOut['S:' + key] = String(this.h1n); this.heads.push({ lvl: 1, n, t });
    this.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, spacing: { after: 280, line: 320, lineRule: 'exact' }, indent: { left: 709, hanging: 709 },
      children: [new TextRun({ text: n + '\t' + t, font: SANS, size: 32, color: ROJO })] }));
  }
  h2(key, t) {
    this.h2n++; const n = this.h1n + '.' + this.h2n;
    this.refsOut['S:' + key] = n; this.heads.push({ lvl: 2, n, t });
    this.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 200 }, children: [new TextRun({ text: n + ' ' + t, font: BODY, bold: true, size: 24 })] }));
  }
  h3(t) { this.push(new Paragraph({ keepNext: true, spacing: { before: 120, after: 120 }, children: [new TextRun({ text: t, font: BODY, bold: true, size: 22 })] })); }
  // ----- texto
  p(t) { this.push(new Paragraph({ spacing: { after: 240, line: 280, lineRule: 'atLeast' }, children: this.runs(t, { size: 22 }) })); }
  ul(items) { items.forEach((t, i) => this.push(new Paragraph({ numbering: { reference: 'bul', level: 0 }, spacing: { after: i === items.length - 1 ? 240 : 100, line: 280, lineRule: 'atLeast' }, children: this.runs(t, { size: 22 }) }))); }
  ol(items) {
    const ref = 'num' + (++this.nol);
    items.forEach((t, i) => this.push(new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: i === items.length - 1 ? 240 : 100, line: 280, lineRule: 'atLeast' }, children: this.runs(t, { size: 22 }) })));
  }
  eq(text, key) {
    this.ne++; if (key) this.refsOut['E:' + key] = String(this.ne);
    this.push(new Paragraph({ tabStops: [{ type: TabStopType.CENTER, position: Math.round(W / 2) }, { type: TabStopType.RIGHT, position: W }], spacing: { before: 60, after: 200, line: 280, lineRule: 'atLeast' },
      children: [new TextRun({ children: [new d.Tab(), text, new d.Tab(), '(' + this.ne + ')'], font: 'Cambria Math', size: 22 })] }));
  }
  donde(items) {            // «donde:» con símbolo y significado
    this.push(new Paragraph({ keepNext: true, spacing: { after: 80 }, children: this.runs('donde:', { size: 22 }) }));
    const w1 = 1700, w2 = W - 1700;
    this.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [w1, w2], rows: items.map(([s, m]) => new TableRow({ cantSplit: true, children: [
      new TableCell({ width: { size: w1, type: WidthType.DXA }, borders: { top: none, left: none, right: none, bottom: { style: BorderStyle.SINGLE, size: 4, color: GRIS2 } }, margins: { top: 30, bottom: 30, left: 85, right: 85 }, children: [new Paragraph({ children: [new TextRun({ text: s, font: 'Cambria Math', size: 20 })] })] }),
      new TableCell({ width: { size: w2, type: WidthType.DXA }, borders: { top: none, left: none, right: none, bottom: { style: BorderStyle.SINGLE, size: 4, color: GRIS2 } }, margins: { top: 30, bottom: 30, left: 85, right: 85 }, children: [new Paragraph({ children: this.runs(m, { size: 18 }) })] })] })) }));
    this.push(this.gap(160));
  }
  code(t) { for (const l of t.split('\n')) this.push(new Paragraph({ spacing: { after: 0, line: 240, lineRule: 'auto' }, shading: { fill: GRIS1, type: ShadingType.CLEAR, color: 'auto' }, indent: { left: 120, right: 120 },
    children: [new TextRun({ text: l || ' ', font: MONO, size: 17 })] })); this.push(this.gap(160)); }
  note(t, kind = 'aviso') {
    const paras = (Array.isArray(t) ? t : [t]).map(x => new Paragraph({ spacing: { before: 40, after: 40, line: 260, lineRule: 'atLeast' }, children: this.runs(x, { size: 20 }) }));
    this.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [W], rows: [new TableRow({ cantSplit: true, children: [new TableCell({ width: { size: W, type: WidthType.DXA },
      borders: { top: none, bottom: none, right: none, left: { style: BorderStyle.SINGLE, size: 24, color: kind === 'info' ? '767171' : ROJO } },
      margins: { top: 80, bottom: 80, left: 160, right: 140 }, shading: { fill: kind === 'info' ? GRIS1 : AVISO, type: ShadingType.CLEAR, color: 'auto' }, children: paras })] })] }));
    this.push(this.gap(200));
  }
  table(key, caption, headers, rows, widths, o = {}) {
    this.nt++; this.refsOut['T:' + key] = String(this.nt);
    const tot = widths.reduce((a, b) => a + b, 0);
    const k = widths.map(x => Math.round(x * W / tot)); k[k.length - 1] += W - k.reduce((a, b) => a + b, 0);
    this.push(new Paragraph({ keepNext: true, spacing: { before: 60, after: 80, line: 240, lineRule: 'auto' }, children: [new TextRun({ text: `Tabla ${this.nt}. `, bold: true, font: BODY, size: 18 }), ...this.runs(caption, { size: 18 })] }));
    const tr = [new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => this.cell(h, k[i], { head: true, fill: GRIS2 })) })];
    for (const r of rows) tr.push(new TableRow({ cantSplit: true, children: r.map((c, i) => this.cell(c, k[i], { align: o.center && i > 0 ? AlignmentType.CENTER : AlignmentType.LEFT, bold: o.firstBold && i === 0 })) }));
    this.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: k, rows: tr }));
    this.push(this.gap(200));
  }
  fig(key, path, caption, wIn = 6.2) {
    this.nf++; this.refsOut['F:' + key] = String(this.nf);
    const sz = require('child_process').execFileSync('python3', ['-I', '-c', 'import sys;from PIL import Image;i=Image.open(sys.argv[1]);print(i.size[0],i.size[1])', path]).toString().trim().split(' ').map(Number);
    const wpx = Math.round(wIn * 96), hpx = Math.round(wpx * sz[1] / sz[0]);
    this.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 100, after: 60 }, children: [new ImageRun({ type: 'png', data: fs.readFileSync(path), transformation: { width: wpx, height: hpx }, altText: { title: 'Figura ' + this.nf, description: caption, name: 'fig' + this.nf } })] }));
    this.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: `Figura ${this.nf}. `, bold: true, font: BODY, size: 18 }), ...this.runs(caption, { size: 18 })] }));
  }
  contents() { this.tocIndex = this.kids.length; }
  build(file) {
    const o = this.opt;
    if (this.tocIndex !== null) {
      const items = [new Paragraph({ heading: HeadingLevel.HEADING_2, pageBreakBefore: true, spacing: { after: 200 }, children: [new TextRun({ text: 'Contenido', font: BODY, bold: true, size: 24 })] })];
      for (const h of this.heads) {
        const key = h.n + ' ' + h.t, pg = this.pages[key];
        const l1 = h.lvl === 1;
        items.push(new Paragraph({ spacing: { before: l1 ? 120 : 0, after: 20, line: 240, lineRule: 'auto' }, indent: { left: l1 ? 0 : 567 },
          tabStops: [{ type: TabStopType.LEFT, position: l1 ? 567 : 1250 }, { type: TabStopType.RIGHT, position: W, leader: LeaderType.DOT }],
          children: [new TextRun({ text: h.n + '\t' + h.t, font: BODY, size: l1 ? 20 : 18, bold: l1 }), new TextRun({ children: [new d.Tab(), pg ? String(pg) : ''], font: BODY, size: l1 ? 20 : 18, bold: l1 })] }));
      }
      this.kids.splice(this.tocIndex, 0, ...items);
    }
    const bullets = { reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '▪', alignment: AlignmentType.LEFT, style: { run: { font: SANS }, paragraph: { indent: { left: 720, hanging: 360 } } } }] };
    const nums = Array.from({ length: this.nol }, (_, i) => ({ reference: 'num' + (i + 1), levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }));
    const logo = fs.readFileSync(__dirname + '/logo.png');
    const header = new Header({ children: [
      new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: W }], spacing: { after: 0 }, children: [
        new ImageRun({ type: 'png', data: logo, transformation: { width: 96, height: 31 }, altText: { title: 'Ternium', description: 'Logotipo', name: 'logo' } }),
        new TextRun({ children: [new d.Tab(), o.cabecera], font: BODY, size: 18 })] }),
      new Paragraph({ children: [] })] });
    const footer = new Footer({ children: [new Paragraph({ children: [new TextRun({ children: [PageNumber.CURRENT], font: BODY, size: 20 })] })] });
    const doc = new d.Document({ creator: 'T&P Refractarios', title: o.titulo, numbering: { config: [bullets, ...nums] },
      styles: { default: { document: { run: { font: BODY, size: 22 } } },
        paragraphStyles: [
          { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: SANS, size: 32, color: ROJO }, paragraph: { outlineLevel: 0, keepNext: true } },
          { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: BODY, size: 24, bold: true }, paragraph: { outlineLevel: 1, keepNext: true, keepLines: true } }] },
      sections: [{ properties: { page: { size: { width: 11907, height: 16839 }, margin: { top: 1276, right: 851, bottom: 851, left: 1134, header: 720, footer: 159 } } },
        headers: { default: header }, footers: { default: footer }, children: this.kids }] });
    fs.writeFileSync(file + '.heads.json', JSON.stringify(this.heads.map(h => h.n + ' ' + h.t)));
    fs.writeFileSync(file + '.refs.json', JSON.stringify(this.refsOut));
    return d.Packer.toBuffer(doc).then(b => fs.writeFileSync(file, b));
  }
}
module.exports = { Builder };
