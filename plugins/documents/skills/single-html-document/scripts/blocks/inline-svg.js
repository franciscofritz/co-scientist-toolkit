const STYLE_ID = 'block-inline-svg-style';
const CSS = `
.block-inline-svg {
  margin: 1.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
.block-inline-svg--center { align-items: center; text-align: center; }
.block-inline-svg--start  { align-items: flex-start; }
.block-inline-svg--end    { align-items: flex-end; text-align: right; }
.block-inline-svg--full   { align-items: stretch; }
.block-inline-svg__figure {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
  max-width: 100%;
}
.block-inline-svg--center .block-inline-svg__figure { align-items: center; }
.block-inline-svg--start  .block-inline-svg__figure { align-items: flex-start; }
.block-inline-svg--end    .block-inline-svg__figure { align-items: flex-end; }
.block-inline-svg--full   .block-inline-svg__figure { align-items: stretch; width: 100%; }
.block-inline-svg__frame {
  display: inline-block;
  background: white;
  padding: 0.6rem;
  border-radius: 6px;
  max-width: 100%;
  box-sizing: border-box;
  /* When the author sets maxHeight in data, that value is applied as inline
     style on this element. We give the inner SVG room to be the limiting
     factor of overall height. */
}
.block-inline-svg--framed .block-inline-svg__frame { border: 1px solid rgba(0, 0, 0, 0.1); }
.block-inline-svg--full .block-inline-svg__frame { display: block; width: 100%; }
.block-inline-svg__frame > svg {
  display: block;
  /* The renderer copies the viewBox aspect into width/height attributes,
     which become the SVG's intrinsic size. CSS only ever shrinks; never
     scales up beyond the natural size unless align is "full". */
  max-width: 100%;
  height: auto;
}
.block-inline-svg--full .block-inline-svg__frame > svg {
  width: 100%;
}
.block-inline-svg__caption {
  font-size: 0.92rem;
  line-height: 1.45;
  color: rgba(0, 0, 0, 0.8);
  margin: 0;
  max-width: 100%;
}
.block-inline-svg__caption p:first-child { margin-top: 0; }
.block-inline-svg__caption p:last-child  { margin-bottom: 0; }
.block-inline-svg__attribution {
  font-size: 0.78rem;
  color: rgba(0, 0, 0, 0.55);
  margin: 0;
}
.block-inline-svg__attribution p { margin: 0; }
`;

function ensureStyle(doc) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = CSS;
  doc.head.appendChild(style);
}

function parseViewBox(s) {
  if (!s) return null;
  const parts = s.trim().split(/[\s,]+/).map(parseFloat);
  if (parts.length < 4) return null;
  const [, , w, h] = parts;
  if (!w || !h) return null;
  return { w, h };
}

export function mount(root, data) {
  const doc = root.ownerDocument;
  ensureStyle(doc);
  const align = ['center', 'start', 'end', 'full'].includes(data.align) ? data.align : 'center';
  root.classList.add('block-inline-svg', `block-inline-svg--${align}`);
  if (data.frame) root.classList.add('block-inline-svg--framed');
  root.innerHTML = '';

  const figure = doc.createElement('figure');
  figure.className = 'block-inline-svg__figure';

  const frameEl = doc.createElement('div');
  frameEl.className = 'block-inline-svg__frame';
  if (data.maxHeight) {
    // Cap the SVG height (not the frame) so width adjusts proportionally.
    // We apply max-height directly to the SVG via a child selector.
    frameEl.style.setProperty('--block-inline-svg-max-height', data.maxHeight);
  }
  frameEl.innerHTML = data.svg || '';

  const svg = frameEl.querySelector('svg');
  if (svg) {
    if (!svg.hasAttribute('preserveAspectRatio')) {
      svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    }
    // Give the SVG an intrinsic size from its viewBox so CSS max-width/height
    // can shrink it without first scaling it up to the parent's full width.
    const vb = parseViewBox(svg.getAttribute('viewBox'));
    if (vb) {
      if (!svg.hasAttribute('width'))  svg.setAttribute('width',  String(vb.w));
      if (!svg.hasAttribute('height')) svg.setAttribute('height', String(vb.h));
    }
    if (data.maxHeight) {
      svg.style.maxHeight = data.maxHeight;
      // Width auto-adjusts to maintain aspect ratio when max-height kicks in.
      svg.style.width = 'auto';
    }
  }
  figure.appendChild(frameEl);

  if (data.captionHtml) {
    const caption = doc.createElement('figcaption');
    caption.className = 'block-inline-svg__caption';
    caption.innerHTML = data.captionHtml;
    figure.appendChild(caption);
  }
  if (data.attributionHtml) {
    const attr = doc.createElement('small');
    attr.className = 'block-inline-svg__attribution';
    attr.innerHTML = data.attributionHtml;
    figure.appendChild(attr);
  }

  root.appendChild(figure);
}
