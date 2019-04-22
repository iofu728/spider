/*
 * @Author: gunjianpan
 * @Date:   2019-04-20 22:21:40
 * @Last Modified by:   gunjianpan
 * @Last Modified time: 2019-04-21 13:18:38
 */

const jsdom = require('jsdom');
const {JSDOM} = jsdom;

function genEleven(script, url, callback) {
  const dom = new JSDOM();
  window = dom.window;
  document = window.document;
  window.decodeURIComponent = decodeURIComponent;
  let href = url
  let userAgent = 'Chrome/73.0.3682.0'
  let geolocation = 0;
  document.createElement('div');
  var div = document.createElement('div');
  div.innerHTML = '333';
  window[callback] =
      function(e) {
    window.AAA = e();
  }

  eval(script);
  console.log(aaa);
  return aaa;
}
url = 'https://hotels.ctrip.com/hotel/4889292.html'

script = 'let aaa = 1;'
genEleven(script, url, 'CASNAuIDNBfCYLBKdi')
