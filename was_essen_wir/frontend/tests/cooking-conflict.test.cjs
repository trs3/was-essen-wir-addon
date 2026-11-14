const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');

require.extensions['.tsx'] = (module, filename) => {
  const {outputText} = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX},
  });
  module._compile(outputText, filename);
};
const {CookingConflictDialog, conflictTiming} = require('../src/CookingConflictDialog.tsx');
const props = {
  dishName: 'Pasta mit Tomatensauce', cookedDay: '2026-11-12',
  plannedDay: '2026-11-16', today: '2026-11-14', busy: false, error: '',
  onReplace() {}, onKeep() {},
};

test('dialog uses the cooking weekday and measures the next appointment from today', () => {
  const html = renderToStaticMarkup(React.createElement(CookingConflictDialog, props));
  assert.match(html, /am Donnerstag, 12\. November gekocht/);
  assert.match(html, /In 2 Tagen \(Montag, 16\. November\)/);
  assert.match(html, /Neuen Vorschlag machen/);
  assert.match(html, />Passt<\/button>/);
  assert.match(html, /role="dialog"/);
});

test('relative dates handle today, tomorrow, the past and daylight saving boundaries', () => {
  assert.match(conflictTiming('2026-11-14', '2026-11-14'), /^Heute/);
  assert.match(conflictTiming('2026-11-15', '2026-11-14'), /^Morgen/);
  assert.match(conflictTiming('2026-11-13', '2026-11-14'), /war es außerdem eingeplant/);
  assert.match(conflictTiming('2026-10-26', '2026-10-24'), /^In 2 Tagen/);
});

function buttons(element) {
  if (!element || typeof element !== 'object') return [];
  if (Array.isArray(element)) return element.flatMap(buttons);
  return [...(element.type === 'button' ? [element] : []), ...buttons(element.props?.children)];
}

test('the two choices call separate handlers and are disabled while saving', () => {
  const calls = [];
  const tree = CookingConflictDialog({...props, onReplace: () => calls.push('replace'), onKeep: () => calls.push('keep')});
  const choices = buttons(tree);
  assert.equal(choices.length, 2);
  choices[0].props.onClick();
  choices[1].props.onClick();
  assert.deepEqual(calls, ['replace', 'keep']);
  assert.ok(buttons(CookingConflictDialog({...props, busy: true})).every(button => button.props.disabled));
});

test('save errors remain visible inside the dialog', () => {
  const html = renderToStaticMarkup(React.createElement(CookingConflictDialog, {...props, error: 'Plan inzwischen geändert'}));
  assert.match(html, /role="alert">Plan inzwischen geändert/);
});
