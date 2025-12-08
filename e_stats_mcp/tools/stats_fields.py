"""統計分野コードのヘルパーツール."""

STATS_FIELDS = [
    {"code": "01", "name": "国土・気象"},
    {"code": "02", "name": "人口・世帯"},
    {"code": "03", "name": "労働・賃金"},
    {"code": "04", "name": "農林水産業"},
    {"code": "05", "name": "鉱工業"},
    {"code": "06", "name": "商業・サービス業"},
    {"code": "07", "name": "企業・家計・経済"},
    {"code": "08", "name": "住宅・土地・建設"},
    {"code": "09", "name": "エネルギー・水"},
    {"code": "10", "name": "運輸・観光"},
    {"code": "11", "name": "情報通信・科学技術"},
    {"code": "12", "name": "教育・文化・スポーツ・生活"},
    {"code": "13", "name": "行財政"},
    {"code": "14", "name": "司法・安全・環境"},
    {"code": "15", "name": "社会保障・衛生"},
    {"code": "16", "name": "国際"},
    {"code": "17", "name": "その他"},
]


async def get_stats_fields() -> list[dict]:
    """統計分野コード一覧を返す."""
    return STATS_FIELDS

