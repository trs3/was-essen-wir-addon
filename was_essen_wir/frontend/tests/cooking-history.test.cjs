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
require.extensions['.ts'] = require.extensions['.tsx'];
const {CookingHistory} = require('../src/CookingHistory.tsx');
const props = {
  today: '2026-11-13', plans: [], history: [],
  dishes: [{id: 1, name: 'Pasta'}, {id: 2, name: 'Suppe'}], busy: false,
  onCook() {}, onChoose() {}, onDelete() {}, onAdd() {},
};
const render = overrides => renderToStaticMarkup(React.createElement(CookingHistory, {...props, ...overrides}));
const row = (html, day) => html.split(/<div class="history-row"[^>]*>/).find(part => part.includes(`dateTime="${day}"`));

test('lists every day including gaps across month boundaries, newest first, excluding future plans', () => {
  const html = render({plans: [{day: '2026-11-14', dish_id: 2, status: 'suggested'}]});
  assert.equal((html.match(/<time /g) || []).length, 7);
  assert.ok(html.indexOf('dateTime="2026-11-13"') < html.indexOf('dateTime="2026-11-12"'));
  assert.ok(row(html, '2026-11-07'));
  assert.ok(!html.includes('dateTime="2026-11-06"'));
  assert.ok(!html.includes('dateTime="2026-11-14"'));
  assert.match(row(html, '2026-11-12'), /Kein Vorschlag gespeichert/);
  assert.match(row(html, '2026-11-12'), /Ändern/);
});

test('unconfirmed, confirmed and fixed proposals can be cooked directly or replaced', () => {
  for (const status of ['suggested', 'confirmed', 'fixed']) {
    const html = render({plans: [{day: props.today, dish_id: 1, status}]});
    const today = row(html, props.today);
    assert.match(today, /<strong>Pasta<\/strong>/);
    assert.match(today, /noch nicht als gekocht erfasst/);
    assert.match(today, /aria-label="[^"]*: Als gekocht speichern"/);
    assert.match(today, />Ändern<\/button>/);
    assert.doesNotMatch(today, /✓ Gekocht/);
  }
});

test('actual cooking takes precedence while preserving the original proposal as context', () => {
  const today = row(render({plans: [{day: props.today, dish_id: 1, status: 'suggested'}],
    history: [{day: props.today, dish_id: 2, id: 7, version: 1}]}), props.today);
  assert.match(today, /<strong>Suppe<\/strong>/);
  assert.match(today, /✓ Gekocht/);
  assert.match(today, /Eigentlich war geplant: Pasta/);
  assert.match(today, />Ändern<\/button>/);
  assert.match(today, /Kochereignis vom .* löschen/);
  assert.doesNotMatch(today, /aria-label="[^"]*: Als gekocht speichern"/);
});

test('free days permit backfilling without a direct cook button', () => {
  const today = row(render({plans: [{day: props.today, dish_id: null, status: 'empty'}]}), props.today);
  assert.match(today, /Nichts gekocht/);
  assert.match(today, /Ändern/);
  assert.doesNotMatch(today, /aria-label="[^"]*: Als gekocht speichern"/);
});

test('cooking without any original proposal remains visible', () => {
  const today = row(render({history: [{day: props.today, dish_id: 2, id: 7, version: 1}]}), props.today);
  assert.match(today, /Suppe/);
  assert.match(today, /✓ Gekocht/);
  assert.doesNotMatch(today, /Eigentlich war geplant:/);
});

test('prevents repeated cooking actions while a save is pending', () => {
  const today = row(render({busy: true, plans: [{day: props.today, dish_id: 1, status: 'suggested'}]}), props.today);
  assert.match(today, /aria-label="[^"]*: Als gekocht speichern" disabled=""/);
  assert.match(today, /disabled="">Ändern/);
});

function withComponentState(check) {
  const original = React.useState;
  let count = 7;
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
    buttons.find(button => button.props['aria-label']?.endsWith('Als gekocht speichern')).props.onClick();
    buttons.find(button => button.props.children === 'Ändern' && !button.props['aria-label']).props.onClick();
    buttons.find(button => button.props['aria-label']?.endsWith('bearbeiten')).props.onClick();
    buttons.find(button => button.props['aria-label']?.endsWith('löschen')).props.onClick();
    assert.deepEqual(calls, [[props.today, 1], [props.today], [event.day, event], [event]]);
  });
});

test('loading older days exposes older saved proposals and cooking events', () => {
  withComponentState(renderTree => {
    const overrides = {plans: [{day: '2026-10-01', dish_id: 1, status: 'suggested'}],
      history: [{id: 5, day: '2026-09-20', dish_id: 2, version: 1}]};
    const tree = renderTree(overrides);
    assert.equal(elements(tree, element => element.type === 'time').length, 7);
    elements(tree, element => element.props?.className === 'history-older')[0].props.onToggle({currentTarget: {open: true}});
    const opened = renderTree(overrides);
    assert.equal(elements(opened, element => element.type === 'time').length, 37);
    elements(opened, element => element.props?.className === 'history-more')[0].props.onClick();
    const expanded = renderTree(overrides);
    const dates = elements(expanded, element => element.type === 'time').map(element => element.props.dateTime);
    assert.equal(dates.length, 67);
    assert.ok(dates.includes('2026-10-01'));
    assert.ok(dates.includes('2026-09-20'));
    assert.ok(elements(expanded, element => element.type === 'strong').some(element => element.props.children === 'Suppe'));
    elements(expanded, element => element.props?.className === 'history-older')[0].props.onToggle({currentTarget: {open: false}});
    assert.equal(elements(renderTree(overrides), element => element.type === 'time').length, 7);
  });
});


test('past firm plans turn orange until cooked, while suggestions and free days keep their state', () => {
  const {planState} = require('../src/planState.ts');
  for (const status of ['confirmed', 'fixed']) {
    assert.equal(planState('2026-11-12', props.today, status, false), 'overdue');
    assert.equal(planState(props.today, props.today, status, false), status);
    assert.equal(planState('2026-11-14', props.today, status, false), status);
    assert.equal(planState('2026-11-12', props.today, status, true), 'cooked');
    const html = render({plans: [{day: '2026-11-12', dish_id: 1, status}]});
    assert.match(html, /class="history-row" data-state="overdue"/);
  }
  assert.equal(planState('2026-11-12', props.today, 'suggested', false), 'suggested');
  assert.equal(planState('2026-11-12', props.today, 'empty', false), 'empty');
  assert.equal(planState('2026-11-12', props.today, undefined, false), 'open');
});


test('nothing cooked is neutral and preserves the original proposal without offering a cook shortcut', () => {
  const today = row(render({plans: [{day: props.today, dish_id: null, original_dish_id: 1, status: 'empty'}]}), props.today);
  assert.match(today, /<strong>Nichts gekocht<\/strong>/);
  assert.match(today, /Als nicht gekocht erfasst/);
  assert.match(today, /Eigentlich war geplant: Pasta/);
  assert.match(today, />Ändern<\/button>/);
  assert.doesNotMatch(today, /Als gekocht speichern/);
});
