from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=options)
    
    script = """
    function getDeepText(node) {
        if (node.nodeType === Node.TEXT_NODE) return node.textContent.trim();
        let res = '';
        if (node.shadowRoot) res += getDeepText(node.shadowRoot);
        for (let child of node.childNodes) {
            res += ' ' + getDeepText(child);
        }
        return res.trim();
    }
    
    let allNodes = document.querySelectorAll('*');
    let results = [];
    for (let i=0; i<allNodes.length; i++) {
        let n = allNodes[i];
        let t = '';
        for (let child of n.childNodes) {
            if (child.nodeType === Node.TEXT_NODE) t += child.textContent.trim() + ' ';
        }
        t = t.trim();
        if (t.length > 50 && n.shadowRoot == null) {
            results.push({tag: n.tagName, class: n.className, text: t.substring(0, 100)});
        }
    }
    return results;
    """
    
    res = driver.execute_script(script)
    for r in res:
        print(f"TAG: {r['tag']}, CLS: {r['class']}")
        print(f"TEXT: {r['text']}")
        print("-" * 20)
    driver.quit()

if __name__ == "__main__":
    main()
