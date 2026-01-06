from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class DiscoveryChannel:
    """Channel definition used to build search queries for discovery.

    The class is intentionally lightweight so it can be reused for
    site-specific search templates (ecommerce, social, docs, analyst reports).
    """

    name: str
    query_template: str
    description: str | None = None

    def build_query(self, keyword: str) -> str:
        return self.query_template.format(keyword=keyword)


BASE_CHANNELS: list[DiscoveryChannel] = [
    DiscoveryChannel(name="general", query_template="{keyword}", description="通用搜索"),
    DiscoveryChannel(name="news", query_template="{keyword} 新闻", description="新闻/资讯"),
    DiscoveryChannel(name="reviews", query_template="{keyword} 评测", description="测评/点评"),
]


CONSUMER_CHANNELS: list[DiscoveryChannel] = [
    DiscoveryChannel(
        name="ecommerce",
        query_template="{keyword} 价格 OR 评测 site:jd.com OR site:taobao.com",
        description="电商与测评",
    ),
    DiscoveryChannel(
        name="video",
        query_template="{keyword} 开箱 OR 体验 视频",
        description="视频开箱/体验",
    ),
    DiscoveryChannel(
        name="community",
        query_template="{keyword} 讨论 forum OR 知乎",
        description="社区讨论",
    ),
]


SOFTWARE_CHANNELS: list[DiscoveryChannel] = [
    DiscoveryChannel(name="docs", query_template="{keyword} documentation", description="官方文档"),
    DiscoveryChannel(name="github", query_template="{keyword} github", description="代码仓库"),
    DiscoveryChannel(
        name="issues",
        query_template="{keyword} bug OR issue tracker",
        description="问题反馈/issue tracker",
    ),
]


B2B_CHANNELS: list[DiscoveryChannel] = [
    DiscoveryChannel(
        name="analyst",
        query_template="{keyword} 市场报告 OR 白皮书",
        description="行业分析/报告",
    ),
    DiscoveryChannel(
        name="review",
        query_template="{keyword} 客户案例 OR 评价 site:g2.com OR site:gartner.com",
        description="第三方/客户案例",
    ),
    DiscoveryChannel(
        name="sales",
        query_template="{keyword} RFP OR 招标 OR 采购",
        description="采购/投标",
    ),
    DiscoveryChannel(
        name="company",
        query_template="{keyword} 企业官网 OR case study",
        description="企业官网与案例",
    ),
]


PRODUCT_TYPE_CHANNEL_MAP: dict[str, list[DiscoveryChannel]] = {
    "consumer": BASE_CHANNELS + CONSUMER_CHANNELS,
    "software": BASE_CHANNELS + SOFTWARE_CHANNELS,
    "b2b": BASE_CHANNELS + B2B_CHANNELS,
}


def get_channels_for_product_type(product_type: str | None) -> List[DiscoveryChannel]:
    normalized = (product_type or "").strip().lower()
    return PRODUCT_TYPE_CHANNEL_MAP.get(normalized, BASE_CHANNELS)


def list_channel_names(product_type: str | None) -> List[str]:
    return [channel.name for channel in get_channels_for_product_type(product_type)]


def merge_channels(*channel_groups: Iterable[DiscoveryChannel]) -> List[DiscoveryChannel]:
    seen = set()
    merged: list[DiscoveryChannel] = []
    for group in channel_groups:
        for channel in group:
            if channel.name in seen:
                continue
            seen.add(channel.name)
            merged.append(channel)
    return merged
