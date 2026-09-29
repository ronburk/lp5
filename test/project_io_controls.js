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
                <button type="button" data-action="export">Export output</button>
            </div>
            <output aria-live="polite" data-status>Ready</output>`;
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
                const editor = document.createElement("lp5-editarticle");
                editor.setArticle(window.Articles.fromURL(model.rootTOC.URL));
                editor.addEventListener("lp5DialogSave", () => {
                    void run("Save article", async () => {
                        const revision = editor.getArticleRevision();
                        await model.storeResource2(revision.URL, revision.toString());
                        editor.remove();
                    });
                }, {once:true});
                document.body.append(editor);
            } else if(action === "create")
                void run("Create article", async () => {
                    const before = new Set(window.LP5.testProjectIO.writes.keys());
                    await model.createEmptyArticle(0, model.rootTOC);
                    const name = [...window.LP5.testProjectIO.writes.keys()]
                        .find(item => /^\d+\.lp5$/.test(item) && !before.has(item));
                    await reloadProject();
                    return `Created ${name || "article"}`;
                });
            else if(action === "export")
                void run("Export output", async () => {
                    views.render();
                    await model.project.write("lp5.html", model.outputText || "");
                    return "Export captured in memory";
                });
        });
    }

    if(document.readyState === "complete") install();
    else window.addEventListener("load", install, {once:true});
})();
