const {Builder, By, Key, until} = require('selenium-webdriver');

(async function example() {
    let driver = await new Builder()
        .forBrowser('chrome')
        .setChromeOptions("--allow-file-access-from-files")
        .build();
    try {
        await driver.get('file:///C:/rlb/code/lp5/new.html#PickOrCreateProject')
            .sleep(10);
    } finally {
        await driver.wait(()=>{}, 1000);
        await driver.quit();
    }
})();
