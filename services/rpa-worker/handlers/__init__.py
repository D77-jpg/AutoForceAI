
from .zhihu_handler import ZhihuHandler
from .media_handler import MediaHandler
from .social_platform_handler import SocialHandler
from .baike_handler import BaikeHandler
from .linkedin_handler import LinkedInHandler
from .wordpress_handler import WordPressHandler
from .x_handler import XHandler

def get_handler(platform_type: str, page):
    platform_type = (platform_type or "").lower()
    if platform_type in ["social_qa", "zhihu"]:
        return ZhihuHandler(page)
    elif platform_type in ["media"]:
        return MediaHandler(page)
    elif platform_type in ["wordpress", "website", "wp"]:
        return WordPressHandler(page)
    elif platform_type in ["linkedin"]:
        return LinkedInHandler(page)
    elif platform_type in ["x", "twitter"]:
        return XHandler(page)
    elif platform_type in ["redbook", "tiktok", "wechat", "douyin", "xiaohongshu"]:
        return SocialHandler(page)
    elif platform_type in ["baidu_baike", "baike", "wiki"]:
        return BaikeHandler(page)
    return None
