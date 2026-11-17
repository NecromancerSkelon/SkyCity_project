"""Original score-based epilogues for the completed floating city."""

ENDINGS = (
    {
        "tier": 100,
        "title": "云上之城",
        "body": (
            "最后一片屋檐落下，整座岛在晚风中稳稳升起。"
            "灯火沿着街巷接到山顶，云层从岩壁下缓缓退开。"
            "远航的飞艇放慢速度，船上的人挤到舷边，想记住这座城市的模样。"
        ),
    },
    {
        "tier": 90,
        "title": "天际归航",
        "body": (
            "风吹过连成一片的屋顶，第一盏灯在街头亮起。"
            "城里还留着几处可以修整的地方，居民已经端着晚饭走上露台。"
            "天边的飞艇认出了灯火，开始向这座岛靠拢。"
        ),
    },
    {
        "tier": 80,
        "title": "云间灯火",
        "body": (
            "屋檐之间仍有空隙，几条小路却已经通到了彼此的门前。"
            "傍晚有人把一盏灯挂上高塔，归来的船循着它穿过云雾。"
            "这里的日子才刚开始，窗台上的花还没有开全。"
        ),
    },
    {
        "tier": 70,
        "title": "风中街巷",
        "body": (
            "新铺的小路绕过岩石，工匠还在给街边的扶手拧上最后几颗螺钉。"
            "风从屋檐之间穿过，吹响了窗边的铃。"
            "有人把晚饭送到路口，等忙碌的人一同回家。"
        ),
    },
    {
        "tier": 60,
        "title": "初成浮岛",
        "body": (
            "城市的轮廓刚刚连起来，岩层上还能看见施工留下的痕迹。"
            "居民沿着新路搬进房屋，把种子撒在水渠旁。"
            "夜里风大，几扇亮着的窗替过路的船照出了岸边。"
        ),
    },
    {
        "tier": 0,
        "title": "云上初居",
        "body": (
            "屋顶在风里轻轻作响，几处街巷还显得生疏。"
            "工匠收起工具，在核心旁支起一张桌子；有人带来热汤，大家挪出位置坐下。"
            "岛上的第一个夜晚，就这样开始了。"
        ),
    },
)

STYLE_LINES = {
    "natural": "一粒种子随风落下，停在岩缝里湿润的泥土上。",
    "industrial": "塔里的机轮慢慢转动，夜班工匠推开了临风的窗。",
    "living": "街边传来碗筷碰响的声音，有人给迟归的人留着一碗饭。",
    "hybrid": "晚风掠过不同颜色的屋檐，把一阵笑声带到岛外。",
}


def get_ending(score, style="hybrid"):
    """Return a fresh epilogue dictionary for an integer score from 0 to 100."""
    if isinstance(score, bool) or not isinstance(score, int):
        raise TypeError("score must be an integer")
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")
    ending = next(entry for entry in ENDINGS if score >= entry["tier"])
    return {**ending, "style_line": STYLE_LINES.get(style, STYLE_LINES["hybrid"])}
