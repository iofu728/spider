const jsdom = require('jsdom');
const {
    JSDOM
} = jsdom;

function get_css(html) {
    const dom = new JSDOM(html);
    window = dom.window;
    document = window.document;
    window.decodeURIComponent = decodeURIComponent;

    const script_element = document.querySelector('script');
    const script = script_element.innerHTML;
    eval(script);
    return window.document.querySelector('style').sheet.toString();
}