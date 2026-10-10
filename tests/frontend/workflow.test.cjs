const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function harness() {
  const element = () => ({
    value: '', hidden: false, disabled: false, textContent: '', style: {},
    classList: {toggle() {}}, setAttribute() {}, addEventListener() {},
    querySelector() {return element();}, getContext() {return {clearRect() {}};},
    replaceChildren() {}, append() {}, getBoundingClientRect() {return {width: 800, height: 600};},
  });
  const context = vm.createContext({
    document: {querySelector: element, createElement: element, addEventListener() {}},
    window: {addEventListener() {}},
    ResizeObserver: class {observe() {}}, Image: class {},
    fetch: async () => ({ok: false, status: 409, statusText: 'No dataset', json: async () => ({})}),
    setTimeout: () => 1, clearTimeout() {}, console,
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../../smart_labelimg/web/static/app.js'), 'utf8'), context);
  vm.runInContext(`
    renderAll = () => {}; renderImageList = () => {}; renderNavigation = () => {};
    updateHistoryButtons = () => {}; drawCanvas = () => {}; toast = () => {};
    saveAnnotations = async () => true;
    state.images = [{name: 'first.png'}, {name: 'second.png'}];
    state.currentIndex = 0;
    loadImageWithoutBusy = async (index) => {
      state.currentIndex = index; state.boxes = []; state.history = []; state.historyIndex = -1; snapshot();
    };
  `, context);
  return (script) => vm.runInContext(script, context);
}

// Exercise real workflow functions, not source-string markers.
test('mixed propagation retains candidates and can undo committed boxes', async () => {
  const run = harness();
  await run(`
    api = async () => ({boxes: [{label:'car',x1:1,y1:2,x2:20,y2:30}], candidates: [{box:{label:'car',x1:30,y1:2,x2:50,y2:30}}]});
    smartNext();
  `);
  assert.equal(run('state.boxes.length'), 1);
  assert.equal(run('state.pendingCandidates.length'), 1);
  run('acceptPendingCandidates()');
  assert.equal(run('state.boxes.length'), 2);
  run('restoreHistory(0)');
  assert.equal(run('state.boxes.length'), 0);
});

test('smart next preserves annotations already present on target image', async () => {
  const run = harness();
  await run(`
    api = async () => ({boxes: [{label:'new',x1:1,y1:2,x2:20,y2:30}], candidates: []});
    loadImageWithoutBusy = async () => {state.currentIndex=1;state.boxes=[{label:'existing',x1:1,y1:1,x2:10,y2:10}];};
    smartNext();
  `);
  assert.equal(run('state.boxes[0].label'), 'existing');
});

test('copy previous locks navigation until request completes', async () => {
  const run = harness();
  const promise = run(`
    state.currentIndex = 1;
    let resolveCopy;
    api = () => new Promise(resolve => {resolveCopy = resolve;});
    copyPreviousBoxes();
  `);
  assert.equal(run('state.busy'), true);
  run(`resolveCopy({boxes:[{label:'car',x1:1,y1:2,x2:20,y2:30}]})`);
  await promise;
  assert.equal(run('state.busy'), false);
  assert.equal(run('state.boxes.length'), 1);
});

test('cancelled drag restores original coordinates without saving', () => {
  const run = harness();
  run(`state.boxes=[{x1:99}];state.pointer={kind:'move',originals:[{x1:5}]};cancelPointer();`);
  assert.equal(run('state.boxes[0].x1'), 5);
  assert.equal(run('state.pointer'), null);
  assert.equal(run('state.dirty'), false);
});
