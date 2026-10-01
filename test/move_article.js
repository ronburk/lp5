// Run through the explicit test adapter's “Test article moves” button.
export async function run_move_article_tests(app_model) {
    let passed = 0;
    function check(condition, message) {
        if(!condition) throw new Error(message);
        passed++;
    }
    function fixture(fail_at = []) {
        const documents = {
            'root.lp5': '<template><heading>Root</heading><children><li id="a.lp5"/><li id="b.lp5"/><li id="c.lp5"/></children></template>',
            'a.lp5': '<template><children><li id="d.lp5"/></children><heading>A</heading><section data-lp5-kind="code"><name>Bundle</name><code><![CDATA[x < y]]></code></section></template>',
            'b.lp5': '<template><heading>B</heading><keywords><li>Keep</li></keywords></template>',
            'c.lp5': '<template><heading>C</heading></template>',
            'd.lp5': '<template><heading>D</heading></template>'
        };
        const files = new Map(Object.entries(documents));
        const original = new Map(files);
        const articles = new Map([...files].map(([URL, text]) => [URL, {
            URL, template:new DOMParser().parseFromString(text, 'application/xml').documentElement
        }]));
        for(const [name, parent] of Object.entries({'a.lp5':'root.lp5', 'b.lp5':'root.lp5', 'c.lp5':'root.lp5', 'd.lp5':'a.lp5'}))
            articles.get(name).parentURL = articles.get(parent);
        const writes = [];
        const model = {
            rootTOC:articles.get('root.lp5'),
            articleFromURL:url => articles.get(url),
            project:{
                read:async url => files.get(url),
                write:async (url, text) => {
                    writes.push(url);
                    files.set(url, text); // Deliberately fail AFTER mutation.
                    if(fail_at.includes(writes.length)) throw new Error(`write ${writes.length} failed`);
                }
            }
        };
        return {files, original, articles, writes, model,
            move:(...args) => app_model.move_article.call(model, ...args),
            children:url => [...new DOMParser().parseFromString(files.get(url), 'application/xml')
                .querySelectorAll('template > children > li')].map(li => li.id).join(',')};
    }
    let f = fixture();
    await f.move('c.lp5', 'a.lp5', -1);
    check(f.children('root.lp5') === 'c.lp5,a.lp5,b.lp5', 'Before placement');
    check(f.writes.length === 1, 'Sibling reorder writes one parent');
    f = fixture();
    await f.move('a.lp5', 'c.lp5', 1);
    check(f.children('root.lp5') === 'b.lp5,c.lp5,a.lp5', 'After placement');
    check(f.files.get('a.lp5') === f.original.get('a.lp5'), 'Moved subtree file unchanged');
    f = fixture();
    await f.move('a.lp5', 'b.lp5', 0);
    check(f.children('root.lp5') === 'b.lp5,c.lp5' && f.children('b.lp5') === 'a.lp5', 'Reparent into empty destination');
    check(f.children('a.lp5') === 'd.lp5', 'Descendants retained');
    check(f.writes.join(',') === 'b.lp5,root.lp5', 'Destination written first');
    check(f.files.get('b.lp5').includes('<li>Keep</li>'), 'Parent metadata preserved');
    check(f.files.get('a.lp5') === f.original.get('a.lp5') && f.files.get('d.lp5') === f.original.get('d.lp5'), 'Article content and code unchanged');
    check(f.articles.get('root.lp5').template.querySelectorAll('children > li').length === 3, 'Loaded model untouched until reload');
    f = fixture();
    await f.move('b.lp5', 'a.lp5', 0);
    check(f.children('a.lp5') === 'b.lp5,d.lp5', 'First child before existing children');
    f = fixture();
    await f.move('d.lp5', 'root.lp5', 0);
    check(f.children('root.lp5') === 'd.lp5,a.lp5,b.lp5,c.lp5' && f.children('a.lp5') === '', 'Move up to root');
    for(const args of [['a.lp5','b.lp5',-1], ['b.lp5','a.lp5',1], ['d.lp5','a.lp5',0]]) {
        f = fixture();
        check(await f.move(...args) === false && f.writes.length === 0, 'No-op does not write');
    }
    for(const args of [['root.lp5','a.lp5',0], ['a.lp5','a.lp5',0], ['a.lp5','d.lp5',0], ['a.lp5','d.lp5',1], ['a.lp5','root.lp5',1], ['missing','a.lp5',0], ['a.lp5','b.lp5',7]]) {
        f = fixture();
        let rejected = false;
        try { await f.move(...args); } catch { rejected = true; }
        check(rejected && f.writes.length === 0, 'Invalid move rejected without writes');
    }
    for(const failure of [1, 2]) {
        f = fixture([failure]);
        let rejected = false;
        try { await f.move('a.lp5','b.lp5',0); } catch { rejected = true; }
        check(rejected && [...f.original].every(([url, text]) => f.files.get(url) === text), `Write ${failure} restored exactly`);
    }
    f = fixture([1]);
    try { await f.move('a.lp5','c.lp5',1); } catch {}
    check([...f.original].every(([url, text]) => f.files.get(url) === text), 'Same-parent failed write restored');
    f = fixture([2, 3, 4]);
    let error;
    try { await f.move('a.lp5','b.lp5',0); } catch(e) { error = e; }
    check(error?.rollback_failed && error.message.includes('root.lp5') && error.message.includes('b.lp5'), 'Restoration failures identify both parents');
    return `${passed} article move checks passed`;
}
