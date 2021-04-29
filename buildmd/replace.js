/**
 * @Author: gunjianpan
 * @Date:   2021-04-30 01:49:27
 * @Last Modified by:   gunjianpan
 * @Last Modified time: 2021-04-30 02:39:45
 */

// find tpwds length
content = wx.cgiData.app_msg_info["item"][0]["content"]
content.match(/\p{Sc}\w{8,12}\p{Sc}/gu)

// replace tpwds Part.1
content = infos["item"][0]["multi_item"][0]["content"]
tpwds = content.match(/\p{Sc}\w{8,12}\p{Sc}/gu)
r_tpwds = []
for(let i = 0; i < tpwds.length; i++){
    tpwd = tpwds[i];
    r_tpwd = r_tpwds[i];
    tmp = "3" + tpwd + "/"
    if (content.search(tmp) != -1){
        tpwd = tmp;
    }
    tmp = tpwd + "(已失效)"
    if (content.search(tmp) != -1){
        tpwd = tmp;
    }
    content = content.replace(tpwd, r_tpwd);
}

infos["item"][0]["multi_item"][0]["content"] = content
infos["item"][0]["content"] = content

// replace tpwds Part.2
wx.cgiData.app_msg_info["item"][0]["content"] = content
wx.cgiData.app_msg_info["item"][0]["multi_item"][0]["content"] = content


 