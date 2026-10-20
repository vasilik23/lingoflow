// Run shipped TSX handlers with deterministic hooks and deferred I/O.
// Keyed instances are mounted explicitly; this is not a native renderer.
const fs = require('node:fs'), vm = require('node:vm'), ts = require('typescript');
function harness(filename, mocks = {}) {
  let frame;
  const same = (a, b) => a && b && a.length === b.length && a.every((x, i) => Object.is(x, b[i]));
  const hooks = {
    useState(initial) {const f = frame, i = f.cursor++; if (!f.slots[i]) f.slots[i] = {value: typeof initial === 'function' ? initial() : initial}; return [f.slots[i].value, next => {f.slots[i].value = typeof next === 'function' ? next(f.slots[i].value) : next;}];},
    useRef(initial) {const f = frame, i = f.cursor++; if (!f.slots[i]) f.slots[i] = {current: initial}; return f.slots[i];},
    useCallback(fn, deps) {const f = frame, i = f.cursor++; if (!f.slots[i] || !same(f.slots[i].deps, deps)) f.slots[i] = {fn, deps}; return f.slots[i].fn;},
    useEffect(fn, deps) {const f = frame, i = f.cursor++; if (!f.slots[i] || !same(f.slots[i].deps, deps)) {f.slots[i] = {deps}; f.effects.push(() => {f.cleanups[i]?.(); f.cleanups[i] = fn();});}},
  };
  const jsx = (type, props, key) => ({type, props: props || {}, key});
  const native = {StyleSheet: {create: x => x}, useColorScheme: () => 'light'};
  for (const name of ['View', 'Text', 'ScrollView', 'Pressable', 'ActivityIndicator', 'SafeAreaView']) native[name] = name;
  let uuid = 0;
  const module = {exports: {}};
  vm.runInNewContext(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX}}).outputText, {
    module, exports: module.exports, console, AbortController, setTimeout, clearTimeout,
    require(name) {
      if (name in mocks) return mocks[name];
      if (name === 'react') return hooks;
      if (name === 'react/jsx-runtime') return {jsx, jsxs: jsx};
      if (name === 'react-native') return native;
      if (name === 'expo-crypto') return {randomUUID: () => `00000000-0000-4000-8000-${String(++uuid).padStart(12, '0')}`};
      throw Error('Unmocked module: ' + name);
    }, ...mocks.$globals,
  }, {filename});
  function instance() {
    const state = {slots: [], cleanups: [], effects: [], cursor: 0}; let component, props, tree;
    return {
      render(nextProps = props, nextComponent = component) {const prior = frame; frame = state; props = nextProps; component = nextComponent; state.cursor = 0; state.effects = []; tree = component(props); state.effects.forEach(fn => fn()); frame = prior; return tree;},
      get tree() {return tree;},
      unmount() {state.cleanups.forEach(fn => fn?.());},
    };
  }
  const root = instance();
  return {exports: module.exports, render: root.render, get tree() {return root.tree;}, unmount: root.unmount, instance};
}
function text(node) {if (node == null || typeof node === 'boolean') return ''; if (typeof node !== 'object') return String(node); if (Array.isArray(node)) return node.map(text).join(''); return text(node.props?.children);}
function nodes(tree) {if (!tree || typeof tree !== 'object') return []; if (Array.isArray(tree)) return tree.flatMap(nodes); if (typeof tree.type === 'function') return nodes(tree.type(tree.props)); return [tree, ...nodes(tree.props.children)];}
function button(tree, title) {const found = nodes(tree).find(n => n.type === 'Pressable' && text(n) === title); if (!found) throw Error('Missing button: ' + title); return found.props;}
function deferred() {let resolve, reject; const promise = new Promise((yes, no) => {resolve = yes; reject = no;}); return {promise, resolve, reject};}
const flush = () => new Promise(resolve => setImmediate(resolve));
module.exports = {harness, button, text, nodes, deferred, flush};
