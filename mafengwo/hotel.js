/*
 * @Author: gunjianpan
 * @Date:   2019-04-18 19:23:33
 * @Last Modified by:   gunjianpan
 * @Last Modified time: 2019-04-22 10:31:47
 */

const jsdom = require('jsdom');
const {
    JSDOM
} = jsdom;

function analysis_js(html, salt, prepare_map) {
    const dom = new JSDOM(html);
    window = dom.window;
    document = window.document;
    window.decodeURIComponent = decodeURIComponent;

    const script_element = document.querySelector('script');
    console.log(script_element);
    const script = script_element.innerHTML;
    eval(script);
    return window['SparkMD5']['hash'](JSON['stringify'](prepare_map) + salt)['slice'](2, 12);
}