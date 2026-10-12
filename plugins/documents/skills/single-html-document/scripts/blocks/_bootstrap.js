// Shared bootstrap for interactive blocks.
//
// Each interactive block's renderer module imports `register` from this file
// and calls `register('<type>', mount)`. At packaging time, the bundler pulls
// in every interactive renderer that the page references, so the registry is
// fully populated by the time `bootstrap()` runs.
//
// Source shape produced by the compiler for an interactive block:
//
//   <div data-block-type="<type>" id="...">
//     <script type="application/json" data-block-payload>
//       { ...validated data... }
//     </script>
//   </div>
//
// On DOMContentLoaded the bootstrap finds every such root, parses its JSON
// payload, and calls the registered `mount(root, data)`. Renderers themselves
// remain pure — they do not register listeners on the document or the window.

const REGISTRY = new Map();

export function register(type, mount) {
  if (typeof type !== 'string' || typeof mount !== 'function') return;
  REGISTRY.set(type, mount);
}

export function getRegistry() {
  return REGISTRY;
}

function readPayload(root) {
  const payloadEl = root.querySelector(':scope > script[type="application/json"][data-block-payload]');
  if (!payloadEl) return {};
  try {
    return JSON.parse(payloadEl.textContent || '{}');
  } catch (err) {
    console.error('[blocks] failed to parse payload for', root.getAttribute('data-block-type'), err);
    return {};
  }
}

export function bootstrap(scope) {
  const doc = scope || (typeof document !== 'undefined' ? document : null);
  if (!doc) return;
  const roots = doc.querySelectorAll('[data-block-type]');
  for (const root of roots) {
    const type = root.getAttribute('data-block-type');
    if (!type || root.hasAttribute('data-block-mounted')) continue;
    const mount = REGISTRY.get(type);
    if (!mount) continue;
    const data = readPayload(root);
    try {
      mount(root, data);
      root.setAttribute('data-block-mounted', '');
    } catch (err) {
      console.error('[blocks] mount failed for', type, err);
    }
  }
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => bootstrap());
  } else {
    bootstrap();
  }
}
