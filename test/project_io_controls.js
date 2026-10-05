// Visible UI controls for testing application actions against the test adapter.
// Loaded only by createTestProjectIO() when the URL contains ?test=1.
(() => {
    function install(){
        if(!window.LP5?.testProjectIO || document.getElementById("lp5-test-controls"))
            return;

        const panel = document.createElement("section");
        panel.id = "lp5-test-controls";
        panel.setAttribute("aria-label", "LP5 test project controls");
        panel.style.cssText = [
            "position:fixed", "right:1rem", "bottom:1rem", "z-index:10000",
            "max-width:20rem", "padding:.75rem", "background:#fff",
            "border:2px solid #315b72", "box-shadow:0 2px 12px #0004",
            "font:14px sans-serif"
        ].join(";");
        panel.innerHTML = `
            <strong>Test project</strong>
            <div style="display:flex;flex-wrap:wrap;gap:.35rem;margin:.5rem 0">
                <button type="button" data-action="reload">Reload project</button>
                <button type="button" data-action="edit">Edit root article</button>
                <button type="button" data-action="create">Create article</button>
                <button type="button" data-action="add-after-0">Add after article 0</button>
                <button type="button" data-action="add-root-child">Add root child</button>
                <button type="button" data-action="export">Export output</button>
                <button type="button" data-action="test-moves">Test article moves</button>
                <button type="button" data-action="test-output-selection">Test output selection</button>
                <button type="button" data-action="inspect-storage">Inspect storage</button>
            </div>
            <output aria-live="polite" data-status>Ready</output>
            <pre data-storage hidden style="max-height:10rem;overflow:auto;white-space:pre-wrap"></pre>`;
        document.body.append(panel);

        const status = panel.querySelector("[data-status]");
        const model = window.LP5.model;
        const views = window.LP5.views;

        async function reloadProject(){
            await model.openProject(model.projectName);
            model.updateDerivedState();
            views.render();
        }
        async function run(label, callback){
            status.textContent = `${label}…`;
            try {
                const result = await callback();
                status.textContent = typeof result === "string"
                    ? result : `${label}: complete`;
            } catch(error) {
                status.textContent = `${label}: ${error.name}: ${error.message}`;
            }
        }

        panel.addEventListener("click", event => {
            const action = event.target.closest("button")?.dataset.action;
            if(!action) return;
            if(action === "reload")
                void run("Reload project", reloadProject);
            else if(action === "edit"){
                document.dispatchEvent(new CustomEvent("lp5EditArticle", {
                    detail: model.rootTOC.URL
                }));
                status.textContent = "Editing root article";
            } else if(action === "create")
                void run("Create article", async () => {
                    const before = new Set(window.LP5.testProjectIO.writes.keys());
                    await model.createEmptyArticle(0, model.rootTOC);
                    const name = [...window.LP5.testProjectIO.writes.keys()]
                        .find(item => /^\d+\.lp5$/.test(item) && !before.has(item));
                    await reloadProject();
                    return `Created ${name || "article"}`;
                });
            else if(action === "add-after-0")
                document.dispatchEvent(new CustomEvent("lp5CodeReferenceContext", {
                    detail: {
                        articleURL: "0.lp5",
                        reference: "Added after article 0",
                        x: window.innerWidth / 2,
                        y: window.innerHeight / 2
                    }
                }));
            else if(action === "add-root-child")
                document.dispatchEvent(new CustomEvent("lp5CodeReferenceContext", {
                    detail: {
                        articleURL: model.rootTOC.URL,
                        reference: "Added as root child",
                        x: window.innerWidth / 2,
                        y: window.innerHeight / 2
                    }
                }));
            else if(action === "export")
                void run("Export output", async () => {
                    views.render();
                    await model.project.write("lp5.html", model.outputText || "");
                    return "Export captured in memory";
                });
            else if(action === "test-moves")
                void run("Article move tests", async () => {
                    const {run_move_article_tests} = await import('./move_article.js');
                    return await run_move_article_tests(model);
                });
            else if(action === "test-output-selection")
                void run("Output selection tests", async () => {
                    const {run_output_selection_tests} = await import('./output_selection.js');
                    return await run_output_selection_tests(model, views);
                });
            else if(action === "inspect-storage"){
                const storage = panel.querySelector('[data-storage]');
                const {writes, removed} = window.LP5.testProjectIO;
                storage.textContent = [
                    `Removed files: ${[...removed].join(', ') || '(none)'}`,
                    `Written files: ${[...writes.keys()].join(', ') || '(none)'}`,
                    ...[...writes].map(([name, text]) => `${name}:\n${text}`)
                ].join('\n\n');
                storage.hidden = false;
                status.textContent = 'Storage shown';
            }
        });
    }

    if(document.readyState === "complete") install();
    else window.addEventListener("load", install, {once:true});
})();
