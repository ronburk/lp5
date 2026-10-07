// Run through the explicit test adapter's “Test output selection” button.
export async function run_output_selection_tests(model, views) {
    if(!window.LP5.testProjectIO)
        throw new Error('Output selection checks require the explicit test adapter');
    let passed = 0;
    function check(condition, message) {
        if(!condition) throw new Error(message);
        passed++;
    }
    const project_io = window.LP5.modProjectIO;
    const original_open = project_io.open_project;
    const original_name = model.projectName;
    const original_selection = model.selected_article_url;
    const original_next_id = model.nextArticleID;
    const project_name = 'output-selection-test.lp5';
    const other_project = 'another-output-selection-test.lp5';
    const quoted_url = 'quote"[4].lp5';
    function article(heading, name, code) {
        return `<template><heading>${heading}</heading>`
            + (name === null ? '' : `<section data-lp5-kind="code"><name>${name}</name><code>${code}</code></section>`)
            + '</template>';
    }
    const root = '<template><heading>Selection fixture</heading><children>'
        + ['0.lp5', '1.lp5', '2.lp5', '3.lp5', quoted_url, '5.lp5', '6.lp5']
            .map(url => `<li id="${url.replaceAll('"', '&quot;')}"/>`).join('')
        + '</children></template>';
    const files = new Map([
        [project_name, root], [other_project, root],
        ['0.lp5', article('Outer first', 'Outer', '<![CDATA[outer-before\n]]><lp5- ref="Inner"/><![CDATA[outer-after\n]]>')],
        ['1.lp5', article('Outer second', 'Outer', '<![CDATA[outer-second\n]]>')],
        ['2.lp5', article('Inner', 'Inner', '<![CDATA[inner-body\n]]>')],
        ['3.lp5', article('Caller', '', '<![CDATA[prefix\n]]><lp5- ref="Outer"/><![CDATA[middle\n]]><lp5- ref="Outer"/><![CDATA[suffix\n]]>')],
        [quoted_url, article('Quoted filename', '', '<![CDATA[quoted-body\n]]>')],
        ['5.lp5', article('Unreferenced', 'Unused', '<![CDATA[unused-body\n]]>')],
        ['6.lp5', article('Empty code', '', '')]
    ]);
    let exported = null;
    project_io.open_project = async name => {
        if(name !== project_name && name !== other_project)
            return original_open(name);
        return {
            async read(url) {
                if(!files.has(url)) throw new Error(`Missing test article ${url}`);
                return files.get(url);
            },
            async write(url, text) {
                if(url === 'lp5.html') exported = text;
                else files.set(url, text);
            }
        };
    };
    const source_view = views.views.home.children.sourceDiv;
    const output_view = views.views.home.children.outputDiv;
    const source = source_view.dataID.outerDiv;
    const output = output_view.dataID.outputDiv;
    const nav = views.views.home.children.tableOfContents.rootNode.shadowRoot;
    const wrappers = url => [...output.querySelectorAll('span[data-ref]')]
        .filter(node => node.dataset.ref === url);
    const occurrence = (url, index = 0) => wrappers(url)[index];
    const selected = () => [...output.querySelectorAll('.lp5-output-selected')];
    const text_runs = url => wrappers(url).flatMap(node =>
        [...node.querySelectorAll(':scope > .lp5-output-text')]);
    const highlighted = node => getComputedStyle(node).backgroundColor === 'rgb(217, 234, 255)';
    async function settle_selection() {
        // TOC/Output clicks queue navigation, then article-selection notifications.
        for(let i = 0; i < 4; ++i) await Promise.resolve();
    }
    async function select_source(url) {
        const node = [...source.children].find(node => node.id === url);
        check(Boolean(node), `Source article exists: ${url}`);
        node.click();
        await settle_selection();
    }
    async function reload(name = project_name) {
        await model.openProject(name);
        model.updateDerivedState();
        views.render();
    }
    function check_output(expected) {
        check(model.outputText === expected, `Selection preserves generated text: ${JSON.stringify(model.outputText)}`);
        check(output.innerText === expected,
            `Selection preserves displayed output text: ${JSON.stringify(output.innerText)}`);
    }
    try {
        await reload();
        const expected = 'prefix\nouter-before\ninner-body\nouter-after\nouter-second\nmiddle\nouter-before\ninner-body\nouter-after\nouter-second\nsuffix\nquoted-body\n';
        check_output(expected);
        check(output.querySelectorAll('.lp5-output-hidden').length === 0, 'Sections are visible by default');
        const firstRepeatedOuter = occurrence('0.lp5', 0);
        const firstRepeatedKey = firstRepeatedOuter.dataset.outputKey;
        firstRepeatedOuter.dispatchEvent(new MouseEvent('click', {bubbles: true, composed: true, ctrlKey: true}));
        check(wrappers('0.lp5').filter(node => node.classList.contains('lp5-output-hidden')).length === 1,
            'Ctrl-click hides only the chosen occurrence of a repeated section');
        check(occurrence('0.lp5', 0).dataset.outputKey === firstRepeatedKey
            && occurrence('0.lp5', 0).querySelector('.lp5-output-placeholder')?.textContent === '⟪ hidden: Outer first ⟫',
            'Hidden occurrence shows its article title and keeps a stable identity');
        check(!occurrence('0.lp5', 1).classList.contains('lp5-output-hidden'),
            'Another occurrence of the same article remains visible');
        check(model.outputText === expected && (output.innerText.match(/outer-before/g) || []).length === 1,
            `Hiding preserves generated text: ${JSON.stringify(model.outputText)}; display: ${JSON.stringify(output.innerText)}`);
        check(output.innerText.includes('⟪ hidden: Outer first ⟫'), 'Placeholder is visible in the Output pane');
        views.render();
        check(occurrence('0.lp5', 0).classList.contains('lp5-output-hidden'), 'Hidden occurrence survives a view rerender');
        occurrence('0.lp5', 0).dispatchEvent(new MouseEvent('click', {bubbles: true, composed: true, ctrlKey: true}));
        check(wrappers('0.lp5').every(node => !node.classList.contains('lp5-output-hidden')),
            'Ctrl-click on a hidden placeholder restores that occurrence');
        check_output(expected);
        check(selected().length === 0, 'A new project has no inherited selection');
        await select_source('0.lp5');
        check(selected().length === 2, 'Both occurrences of the selected article are marked');
        check(text_runs('0.lp5').length === 4 && text_runs('0.lp5').every(highlighted), 'Text before and after nested references is highlighted');
        check(text_runs('2.lp5').every(node => !highlighted(node)), 'Nested expansion is not highlighted with its caller');
        check(text_runs('1.lp5').every(node => !highlighted(node)), 'Other sections in the same bundle are not highlighted');
        check_output(expected);
        await select_source('2.lp5');
        check(selected().length === 2 && selected().every(node => node.dataset.ref === '2.lp5'), 'Selection replaces previous highlights');
        check(text_runs('2.lp5').every(highlighted), 'Every nested occurrence is highlighted');
        await select_source('3.lp5');
        check(text_runs('3.lp5').length === 3 && text_runs('3.lp5').every(highlighted), 'Caller highlights only its own three text runs');
        check(text_runs('0.lp5').every(node => !highlighted(node)), 'Referenced bundle text remains distinct');
        text_runs('2.lp5')[0].click();
        await settle_selection();
        check(model.selected_article_url === '2.lp5' && selected().length === 2, 'Output click selects its originating article');
        const link = [...nav.querySelector('lp5-treeview').shadowRoot.querySelectorAll('a')]
            .find(node => node.getAttribute('href') === '1.lp5');
        link.click();
        await settle_selection();
        check(model.selected_article_url === '1.lp5' && text_runs('1.lp5').every(highlighted), 'TOC selection highlights all occurrences');
        await select_source(quoted_url);
        check(selected().length === 1 && text_runs(quoted_url).every(highlighted), 'Filenames containing quotes and brackets match safely');
        await select_source(project_name);
        check(selected().length === 0, 'Explanation-only article clears previous highlights');
        await select_source('5.lp5');
        check(selected().length === 0, 'Unreferenced named code has no output highlight');
        await select_source('6.lp5');
        check(output.querySelectorAll('.lp5-output-selected > .lp5-output-text').length === 0, 'Empty code produces no highlighted text');
        check_output(expected);
        await select_source('0.lp5');
        views.render();
        check(selected().length === 2 && text_runs('0.lp5').every(highlighted), 'Highlight survives a view rerender');
        check(source.querySelector('article.lp5-selected')?.id === '0.lp5', 'Source selection survives the same rerender');
        check(window.LP5.controller.currentArticle === source.querySelector('article.lp5-selected'), 'Controller points to the newly rendered source node');
        await reload();
        check(model.selected_article_url === '0.lp5' && selected().length === 2, 'Highlight survives a same-project reload');
        check_output(expected);
        await model.project.write('lp5.html', model.outputText);
        check(exported === expected, 'Export is byte-for-byte unchanged by highlighting');
        files.set('0.lp5', files.get('0.lp5').replace('outer-after', 'edited-after'));
        await reload();
        check(text_runs('0.lp5').every(highlighted) && output.innerText.includes('edited-after'), 'Highlight follows edited article content after reload');
        await select_source('5.lp5');
        files.delete('5.lp5');
        files.set(project_name, root.replace('<li id="5.lp5"/>', ''));
        await reload();
        check(model.selected_article_url === null && selected().length === 0, 'Removing the selected article clears its selection');
        await select_source('0.lp5');
        await reload(other_project);
        check(model.selected_article_url === null && selected().length === 0, 'Switching projects clears selection even when filenames match');
        return `${passed} output selection checks passed`;
    } finally {
        project_io.open_project = original_open;
        await model.openProject(original_name);
        model.updateDerivedState();
        model.selected_article_url = original_selection;
        model.nextArticleID = original_next_id;
        views.render();
    }
}
