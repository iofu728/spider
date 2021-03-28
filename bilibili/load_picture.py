import requests


def load_picture(url: str, idx: int):
    td = requests.get(url)
    picture_path = "bilibili/data/picture/{}.jpg".format(idx)
    with open(picture_path, "wb") as f:
        f.write(td.content)


SPACE_AVS_URL = (
    "http://space.bilibili.com/ajax/member/getSubmitVideos?mid=%s&page=1&pagesize=50"
)
assign_mid = "282849687"
url = SPACE_AVS_URL % assign_mid

header = {
    "Cookie": "",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
}
req = requests.get(url, headers=header)
req_json = req.json()
vlist = req_json["data"]["vlist"]
pic_lists = [(k["title"], k["aid"], k["pic"]) for k in vlist]
for _, k, url in tt:
    load_picture("http:" + url, k)
