from pixivpy3 import AppPixivAPI
from gppt import GetPixivToken
import os
import re

def get_refresh_token() -> str:
    with open("token.txt", "w+") as f:
        if refresh_token := f.read().strip():
            return refresh_token

        g = GetPixivToken(headless=True)
        refresh_token = g.login(username=os.getenv('PIXIV_USERNAME'), password=os.getenv('PIXIV_PASSWORD'))["refresh_token"]
        f.write(refresh_token)
        return refresh_token

def extract_novel_id(url_or_id):
    """
    从Pixiv小说URL或ID中提取小说ID。
    支持如 https://www.pixiv.net/novel/show.php?id=12345678
    """
    if isinstance(url_or_id, int) or url_or_id.isdigit():
        return str(url_or_id)
    match = re.search(r'id=(\d+)', url_or_id)
    if match:
        return match.group(1)
    raise ValueError("无法从输入中解析出Pixiv小说ID")

def get_pixiv_novel(novel_id_or_url):
    """
    输入Pixiv小说ID或URL，返回标题、描述、正文。
    需要Pixiv账号的refresh_token或access_token。
    """
    novel_id = extract_novel_id(novel_id_or_url)
    api = AppPixivAPI()
    api.set_auth(refresh_token=get_refresh_token())
    novel_detail = api.novel_detail(novel_id)
    if not novel_detail or not novel_detail.novel:
        raise ValueError("未找到小说内容")
    return novel_detail

