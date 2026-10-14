// Run through the explicit test adapter's “Test ToC expansion” button.
export async function run_toc_expansion_tests(model, views) {
    let passed = 0;
    function check(condition, message) {
        if(!condition) throw new Error(message);
        passed++;
    }
    const project_io = window.LP5.modProjectIO;
    const original_open = project_io.open_project;
    const original_name = model.projectName;
    const original_selection = model.selected_article_url;
    const first_name = 'toc-state-project.lp5';
    const second_name = 'toc-state-other-project.lp5';
    const root_text = '<template><heading>Root</heading><children>'
        + '<li id="0.lp5"/><li id="1.lp5"/></children></template>';
    const parent_text = '<template><heading>Parent</heading><children>'
        + '<li id="2.lp5"/></children></template>';
    const leaf_text = '<template><heading>Leaf</heading></template>';
    const files = new Map([
        [first_name, root_text], [second_name, root_text],
        ['0.lp5', parent_text], ['1.lp5', leaf_text], ['2.lp5', leaf_text]
    ]);
    const states = new Map();
    project_io.open_project = async name => {
        if(name !== first_name && name !== second_name)
            return original_open(name);
        return {
            async read(url) {
                if(!files.has(url)) throw new Error(`Missing test article ${url}`);
                return files.get(url);
            },
            async write(url, text) { files.set(url, text); },
            async load_toc_expansion() { return [...(states.get(name) || [])]; },
            async save_toc_expansion(urls) { states.set(name, [...new Set(urls)]); }
        };
    };
    const nav = views.views.home.children.tableOfContents.rootNode.shadowRoot;
    const tree = () => nav.querySelector('lp5-treeview');
    const row = url => tree()?.shadowRoot.querySelector(`li[id="${CSS.escape(url)}"]`);
    const expanded = url => row(url)?.classList.contains('expanded') === true;
    async function reload(name) {
        await model.openProject(name);
        model.updateDerivedState();
        views.render();
        await Promise.resolve();
    }
    try {
        await reload(first_name);
        const parent = row('0.lp5');
        check(Boolean(parent?.querySelector(':scope > ul')), 'Parent row has children');
        parent.click();
        await Promise.resolve();
        check(expanded('0.lp5'), 'Clicking the parent triangle expands its children');
        check(states.get(first_name)?.includes('0.lp5'), 'Expansion is saved for this project');
        views.render();
        check(expanded('0.lp5'), 'Expanded state survives a view rerender');
        await reload(first_name);
        check(expanded('0.lp5'), 'Expanded state is restored after project reload');

        await reload(second_name);
        check(!expanded('0.lp5'), 'Another project starts collapsed');
        check(!states.has(second_name), 'Opening another project does not create unrelated state');

        states.set(first_name, ['0.lp5', '1.lp5', 'removed.lp5']);
        await reload(first_name);
        check(expanded('0.lp5'), 'Existing parent preference remains expanded');
        check(JSON.stringify(states.get(first_name)) === JSON.stringify(['0.lp5']),
            'Stale article URLs and leaf URLs are pruned');

        files.set('0.lp5', '<template><heading>Parent now empty</heading></template>');
        await reload(first_name);
        check(states.get(first_name)?.length === 0,
            'A formerly expandable article is pruned when it has no children');
        check(!row('0.lp5')?.querySelector(':scope > ul'),
            'Updated hierarchy renders without a stale child list');
        return `${passed} Table of Contents expansion checks passed`;
    } finally {
        project_io.open_project = original_open;
        await model.openProject(original_name);
        model.selected_article_url = original_selection;
        model.updateDerivedState();
        views.render();
    }
}
