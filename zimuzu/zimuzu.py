"""
@Author: gunjianpan
@Date:   2019-02-28 09:47:06
@Last Modified by:   gunjianpan
@Last Modified time: 2019-04-13 14:11:45
"""

import codecs
import os
import re

from proxy.getproxy import GetFreeProxy
from util.util import begin_time, end_time, can_retry, load_cfg

proxy_req = GetFreeProxy().proxy_req

"""
  * zimuzu @http
  * zmz005.com/XXXXXX
"""

configure_path = "zimuzu/zimuzu.ini"
data_dir = "zimuzu/data/"


class zimuzu:
    """ load download link from zimuzu """

    def __init__(self):
        cfg = load_cfg(configure_path)
        self.zimuzu_id = cfg.get("basic", "zimuzu_id")
        self.drama_name = cfg.get("basic", "drama_name")

    def load_url(self):
        """ load url form zimuzu """

        url = "http://zmz005.com/{}".format(self.zimuzu_id)
        detail = proxy_req(url, 0)
        total = []

        if not detail:
            print("retry")
            if can_retry(url):
                self.load_url()
            return
        season_list = detail.find_all("div", class_="tab-content info-content")[1:]
        for season in season_list:
            quality_list = season.find_all("div", class_="tab-pane")
            url_body = (
                quality_list[1] if "APP" in quality_list[0]["id"] else quality_list[0]
            )
            season_id = re.findall(r"\d+\.?\d*", url_body["id"])[0]
            total.append(season_id)
            if int(season_id) < 12:
                url_body = quality_list[1]

            url_list = url_body.find_all("ul", class_="down-links")
            url = [
                index.find_all("div", class_="copy-link")[1]["data-url"]
                for index in url_list
            ]
            total.append("\n".join(url) + "\n")
        with codecs.open(
            "{}{}".format(data_dir, self.drama_name), "w", encoding="utf-8"
        ) as f:
            f.write("\n".join(total))


if __name__ == "__main__":
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    zimuzu = zimuzu()
    zimuzu.load_url()
