const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');

// Compile the component with the project's existing TypeScript dependency.
require.extensions['.tsx'] = (module, filename) => {
  const {outputText} = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX},
  });
  module._compile(outputText, filename);
};
const {CookingHistory} = require('../src/CookingHistory.tsx');
const props = {
  today: '2026-11-13', plans: [], history: [],
  dishes: [{id: 1, name: 'Pasta'}, {id: 2, name: 'Suppe'}], busy: false,
  onCook() {}, onChoose() {}, onDelete() {}, onAdd() {},
};
const render = overrides => renderToStaticMarkup(React.createElement(CookingHistory, {...props, ...overrides}));
const row = (html, day) => html.split('<div class="history-row">').find(part => part.includes(`dateTime="${day}"`));

test('lists every day including gaps across month boundaries, newest first, excluding future plans', () => {
  const html = render({plans: [{day: '2026-11-14', dish_id: 2, status: 'suggested'}]});
  assert.equal((html.match(/<time /g) || []).length, 30);
  assert.ok(html.indexOf('dateTime="2026-11-13"') < html.indexOf('dateTime="2026-11-12"'));
  assert.ok(row(html, '2026-10-15'));
  assert.ok(!html.includes('dateTime="2026-10-14"'));
  assert.ok(!html.includes('dateTime="2026-11-14"'));
  assert.match(row(html, '2026-11-12'), /Kein Vorschlag gespeichert/);
  assert.match(row(html, '2026-11-12'), /Gericht nachtragen/);
});

test('unconfirmed, confirmed and fixed proposals can be cooked directly or replaced', () => {
  for (const status of ['suggested', 'confirmed', 'fixed']) {
    const html = render({plans: [{day: props.today, dish_id: 1, status}]});
    const today = row(html, props.today);
    assert.match(today, /<strong>Pasta<\/strong>/);
    assert.match(today, /noch nicht als gekocht erfasst/);
    assert.match(today, />Gekocht<\/button>/);
    assert.match(today, />Etwas anderes gekocht<\/button>/);
    assert.doesNotMatch(today, /✓ Gekocht/);
  }
});

test('actual cooking takes precedence while preserving the original proposal as context', () => {
  const today = row(render({plans: [{day: props.today, dish_id: 1, status: 'suggested'}],
    history: [{day: props.today, dish_id: 2, id: 7, version: 1}]}), props.today);
  assert.match(today, /<strong>Suppe<\/strong>/);
  assert.match(today, /✓ Gekocht/);
  assert.match(today, /Geplant: Pasta/);
  assert.match(today, />Ändern<\/button>/);
  assert.match(today, /Kochereignis vom .* löschen/);
  assert.doesNotMatch(today, />Gekocht<\/button>/);
});

test('free days permit backfilling without a direct cook button', () => {
  const today = row(render({plans: [{day: props.today, dish_id: null, status: 'empty'}]}), props.today);
  assert.match(today, /Bewusst frei/);
  assert.match(today, /Gericht nachtragen/);
  assert.doesNotMatch(today, />Gekocht<\/button>/);
});

test('cooking without any original proposal remains visible', () => {
  const today = row(render({history: [{day: props.today, dish_id: 2, id: 7, version: 1}]}), props.today);
  assert.match(today, /Suppe/);
  assert.match(today, /✓ Gekocht/);
  assert.doesNotMatch(today, /Geplant:/);
});

test('prevents repeated cooking actions while a save is pending', () => {
  const today = row(render({busy: true, plans: [{day: props.today, dish_id: 1, status: 'suggested'}]}), props.today);
  assert.match(today, /disabled="">Gekocht/);
  assert.match(today, /disabled="">Etwas anderes gekocht/);
});

function withComponentState(check) {
  const original = React.useState;
  let count = 30;
  React.useState = () => [count, update => { count = update(count); }];
  try { check(overrides => CookingHistory({...props, ...overrides})); }
  finally { React.useState = original; }
}

function elements(tree, predicate) {
  if (!tree || typeof tree !== 'object') return [];
  if (Array.isArray(tree)) return tree.flatMap(child => elements(child, predicate));
  return [...(predicate(tree) ? [tree] : []), ...elements(tree.props?.children, predicate)];
}

test('row actions pass the exact date, proposed dish or cooking event to their handlers', () => {
  withComponentState(renderTree => {
    const calls = [];
    const event = {id: 7, day: '2026-11-12', dish_id: 2, version: 3};
    const tree = renderTree({plans: [{day: props.today, dish_id: 1, status: 'suggested'}], history: [event],
      onCook: (...args) => calls.push(args), onChoose: (...args) => calls.push(args), onDelete: (...args) => calls.push(args)});
    const buttons = elements(tree, element => element.type === 'button');
    buttons.find(button => button.props.children === 'Gekocht').props.onClick();
    buttons.find(button => button.props.children === 'Etwas anderes gekocht').props.onClick();
    buttons.find(button => button.props.children === 'Ändern').props.onClick();
    buttons.find(button => button.props.children === '×').props.onClick();
    assert.deepEqual(calls, [[props.today, 1], [props.today], [event.day, event], [event]]);
  });
});

test('loading older days exposes older saved proposals and cooking events', () => {
  withComponentState(renderTree => {
    const overrides = {plans: [{day: '2026-10-01', dish_id: 1, status: 'suggested'}],
      history: [{id: 5, day: '2026-09-20', dish_id: 2, version: 1}]};
    const tree = renderTree(overrides);
    elements(tree, element => element.props?.className === 'history-more')[0].props.onClick();
    const expanded = renderTree(overrides);
    const dates = elements(expanded, element => element.type === 'time').map(element => element.props.dateTime);
    assert.equal(dates.length, 60);
    assert.ok(dates.includes('2026-10-01'));
    assert.ok(dates.includes('2026-09-20'));
    assert.ok(elements(expanded, element => element.type === 'strong').some(element => element.props.children === 'Suppe'));
  });
});
