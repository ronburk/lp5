const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class FakeRequest {}

class FakeDatabase {
    constructor() {
        this.stores = new Map();
        this.writeQueue = Promise.resolve();
        this.objectStoreNames = {contains: name => this.stores.has(name)};
    }
    createObjectStore(name) {
        this.stores.set(name, new Map());
        return {};
    }
    transaction(name, mode) {
        return new FakeTransaction(this, name, mode);
    }
    close() {}
}

class FakeTransaction {
    constructor(database, name, mode) {
        this.database = database;
        this.values = database.stores.get(name);
        this.mode = mode;
        this.started = false;
    }
    objectStore() {
        return {
            get: key => {
                const request = new FakeRequest();
                const start = () => setImmediate(() => {
                    request.result = this.values.get(key);
                    request.onsuccess?.();
                    setImmediate(() => {
                        this.oncomplete?.();
                        this.release?.();
                    });
                });
                if (this.mode === "readwrite") {
                    this.database.writeQueue = this.database.writeQueue.then(() =>
                        new Promise(resolve => {
                            this.release = resolve;
                            start();
                        })
                    );
                } else {
                    start();
                }
                return request;
            },
            put: (value, key) => this.values.set(key, value)
        };
    }
}

class FakeIndexedDB {
    database = null;
    open() {
        const request = new FakeRequest();
        setImmediate(() => {
            const fresh = !this.database;
            if (fresh) this.database = new FakeDatabase();
            request.result = this.database;
            if (fresh) request.onupgradeneeded?.();
            request.onsuccess?.();
        });
        return request;
    }
    deleteDatabase() {
        const request = new FakeRequest();
        setImmediate(() => {
            this.database = null;
            request.onsuccess?.();
        });
        return request;
    }
}

function makeUtility(source, sharedIndexedDB, id) {
    const context = {
        window: {indexedDB: sharedIndexedDB},
        crypto: {randomUUID: () => id()},
        Object
    };
    vm.runInNewContext(source + "\nglobalThis.result = indexedDB;", context);
    return context.result;
}

async function main() {
    const source = fs.readFileSync(process.argv[2], "utf8");
    const sharedIndexedDB = new FakeIndexedDB();
    let nextId = 0;
    const id = () => `project-${++nextId}`;
    const firstTab = makeUtility(source, sharedIndexedDB, id);
    const secondTab = makeUtility(source, sharedIndexedDB, id);
    const projectA = {key: "A", async isSameEntry(other) { return this.key === other.key; }};
    const projectB = {key: "B", async isSameEntry(other) { return this.key === other.key; }};

    const [namedA, namedB] = await Promise.all([
        firstTab.addHandle(projectA), secondTab.addHandle(projectB)
    ]);
    assert.notEqual(namedA.id, namedB.id);
    let handles = await firstTab.loadHandles();
    assert.equal(Object.keys(handles).length, 2);
    assert.equal(handles[namedA.id].directoryHandle.key, "A");
    assert.equal(handles[namedB.id].directoryHandle.key, "B");

    const [duplicateA, duplicateB] = await Promise.all([
        firstTab.addHandle(projectA), secondTab.addHandle(projectA)
    ]);
    assert.equal(duplicateA.id, namedA.id);
    assert.equal(duplicateB.id, namedA.id);
    handles = await secondTab.loadHandles();
    assert.equal(Object.keys(handles).length, 2);

    await firstTab.deleteHandle(namedA);
    await secondTab.deleteHandle(namedA);
    await secondTab.deleteHandle(namedB);
    handles = await firstTab.loadHandles();
    assert.deepEqual(Object.keys(handles), []);
    await firstTab.addHandle(projectB);
    await secondTab.deleteDatabase();
    assert.deepEqual(Object.keys(await firstTab.loadHandles()), []);
    console.log("PASS: concurrent additions preserve distinct handles, deduplicate equivalent handles, delete idempotently, and reset the database");
}

main().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
