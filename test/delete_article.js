// Run with node test/delete_article.js. Browser hierarchy checks are documented
// in PROJECT_IO_PREVIEW.md; these checks cover the project-store removal contract.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'new.html'), 'utf8');

function factory(name, end_marker, globals) {
    const start = source.indexOf(`function ${name}(){`);
    const end = source.indexOf(end_marker, start);
    assert(start >= 0 && end > start, `Cannot find ${name}`);
    return vm.runInNewContext(`(${source.slice(start, end).trim()})()`, globals);
}

async function check_native_store() {
    const calls = [];
    const denied = Object.assign(new Error('Permission denied'), {name: 'NotAllowedError'});
    const directory = Object.assign(new Error('Not a file'), {name: 'TypeMismatchError'});
    const handle = {
        name: 'fixture.lp5',
        async queryPermission() { return 'granted'; },
        async getFileHandle(name) {
            if(name === 'missing.lp5')
                throw Object.assign(new Error('Missing'), {name: 'NotFoundError'});
            if(name === 'directory.lp5')
                throw directory;
            return {};
        },
        async removeEntry(...args) {
            calls.push(args);
            if(args[0] === 'denied.lp5')
                throw denied;
        }
    };
    const io = factory('createProductionProjectIO', '// Test mode is opt-in', {
        window: {LP5: {modIndexedDB: {get: async () => handle, put: async () => {}}}},
        console: {log() {}, error() {}}
    });
    assert.equal(await io.load_previous_project(), 'fixture.lp5');
    const store = await io.open_project('fixture.lp5');
    assert.equal(await store.remove('0.lp5'), true);
    assert.equal(await store.remove('missing.lp5'), true);
    await assert.rejects(store.remove('denied.lp5'), error => error === denied);
    await assert.rejects(store.remove('directory.lp5'), error => error === directory);
    // No recursive removal option is allowed: the operation deletes one file.
    assert.deepEqual(calls, [['0.lp5'], ['denied.lp5']]);
}

function test_io(query = '') {
    const window = {LP5: {}};
    const io = factory('createTestProjectIO', 'window.LP5.modProjectIO =', {
        URL,
        location: {href: `https://lp5.test/new.html?test=1${query}`},
        window,
        document: {createElement: () => ({}), head: {append() {}}},
        fetch: async () => ({ok: true, text: async () => '<template/>'})
    });
    return {io, state: window.LP5.testProjectIO};
}

async function check_test_store() {
    const {io, state} = test_io();
    const store = await io.open_project('lp5-test-project.lp5');
    assert.equal(await store.read('0.lp5'), '<template/>');
    await store.remove('0.lp5');
    assert(state.removed.has('0.lp5'));
    await assert.rejects(store.read('0.lp5'), /file not found/);
    const reopened = await io.open_project('lp5-test-project.lp5');
    await assert.rejects(reopened.read('0.lp5'), /file not found/);

    await store.write('0.lp5', '<template><heading>Replacement</heading></template>');
    assert(!state.removed.has('0.lp5'));
    assert.match(await reopened.read('0.lp5'), /Replacement/);
    await store.remove('0.lp5');
    assert(!state.writes.has('0.lp5'));
    assert.equal(await store.create_unique_article('%d.lp5', -1), '0.lp5');
    assert(!state.removed.has('0.lp5'));
    assert.equal(await store.read('0.lp5'), '');

    const failed = test_io('&fail-remove=0.lp5');
    const failed_store = await failed.io.open_project('lp5-test-project.lp5');
    await assert.rejects(failed_store.remove('0.lp5'), /Controlled fixture removal failure/);
    assert.equal(failed.state.removed.size, 0);
    assert.equal(await failed_store.read('0.lp5'), '<template/>');
}

(async () => {
    await check_native_store();
    await check_test_store();
    console.log('Project-store deletion checks passed');
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
