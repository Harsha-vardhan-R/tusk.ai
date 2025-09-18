console.log("Content script loaded");

const getHTML = () : string => {
    const clonedDoc = document.documentElement.cloneNode(true) as HTMLElement;

    const removableElements = clonedDoc.querySelectorAll('script, style, link[rel="stylesheet"]');
    removableElements.forEach(el => el.remove());
    const cleanHtml = clonedDoc.outerHTML;

    return cleanHtml;
}

browser.runtime.onMessage.addListener((
    message,
    sender,
    sendResponse: (response : string) => void
) : boolean => {
    if (message.action! === 'GET_HTML') {
        Promise.resolve(getHTML()).then(sendResponse);
        return true;
    } else {
        return false;
    }
})
