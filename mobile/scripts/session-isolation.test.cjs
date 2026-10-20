const {test} = require('node:test'), assert = require('node:assert/strict'), path = require('node:path');
const {harness, deferred, flush} = require('./component-harness.cjs');
const session = (id, token = id) => ({user: {id}, access_token: token});
function fixture() {
  const initial = deferred(); let notify;
  const mocks = {
    './src/lib/supabase': {supabase: {auth: {getSession: () => initial.promise, onAuthStateChange(fn) {notify = fn; return {data: {listener: null, subscription: {unsubscribe() {}}}};}, startAutoRefresh() {}, stopAutoRefresh() {}}}},
    './src/theme': {palette: () => ({})}, 'expo-status-bar': {StatusBar: 'StatusBar'},
    'react-native': {SafeAreaView: 'SafeAreaView', StyleSheet: {create: x => x}, useColorScheme: () => 'light', AppState: {addEventListener: () => ({remove() {}})}},
  };
  for (const name of ['Login','Today','Lesson','Feedback','Review','Reading','Listening','Profile','Achievements','History','Diagnostic','Writing','Interaction','Practice']) mocks['./src/components/'+name+'Screen'] = {[name+'Screen']: name+'Screen'};
  const h = harness(path.join(__dirname, '../App.tsx'), mocks); h.render({}, h.exports.default);
  const screen = () => h.tree.props.children[1];
  return {h, initial, screen, notify: next => {notify('SIGNED_IN', next); h.render();}};
}
test('account changes remount navigation, while token refresh keeps the same learner route', () => {
  const {h, notify, screen} = fixture(); notify(session('A'));
  const first = screen(); assert.equal(first.key, 'A');
  const learner = h.instance(); learner.render(first.props, first.type);
  learner.tree.props.onOpenLesson('lesson-A'); learner.render(); assert.equal(learner.tree.type, 'LessonScreen');
  notify(session('A', 'refreshed')); const refreshed = screen(); assert.equal(refreshed.key, first.key);
  learner.render(refreshed.props, refreshed.type); assert.equal(learner.tree.type, 'LessonScreen'); assert.equal(learner.tree.props.session.access_token, 'refreshed');
  notify(session('B')); const second = screen(); assert.notEqual(second.key, first.key); learner.unmount();
  const next = h.instance(); next.render(second.props, second.type); assert.equal(next.tree.type, 'TodayScreen'); assert.equal(next.tree.props.session.user.id, 'B');
});
test('logout removes learner navigation even when the same account signs in again', () => {
  const {h, notify, screen} = fixture(); notify(session('A')); const node = screen(), learner = h.instance(); learner.render(node.props, node.type);
  learner.tree.props.onOpenProfile(); learner.render(); assert.equal(learner.tree.type, 'ProfileScreen');
  notify(null); assert.equal(screen().type, 'LoginScreen'); learner.unmount();
  notify(session('A')); const fresh = h.instance(); fresh.render(screen().props, screen().type); assert.equal(fresh.tree.type, 'TodayScreen');
});
test('a late initial session cannot replace a newer auth event', async () => {
  const {h, notify, initial, screen} = fixture(); notify(session('B')); initial.resolve({data: {session: session('A')}}); await flush(); h.render(); assert.equal(screen().key, 'B');
  const loggedOut = fixture(); loggedOut.notify(null); loggedOut.initial.resolve({data: {session: session('A')}}); await flush(); loggedOut.h.render(); assert.equal(loggedOut.screen().type, 'LoginScreen');
});
test('session bootstrap failure does not leave login stuck loading', async () => {
  const {h, initial, screen} = fixture(); initial.reject(Error('secure storage unavailable')); await flush(); h.render(); assert.equal(screen().props.booting, false);
});
