from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MetaLeadProfile:
    platform: str
    profile_url: str
    business_name: str = ""
    category: str = ""
    whatsapp: Optional[str] = None
    website: Optional[str] = None

    facebook: Dict[str, Any] = field(
        default_factory=dict
    )

    instagram: Dict[str, Any] = field(
        default_factory=dict
    )

    ads: Dict[str, Any] = field(
        default_factory=dict
    )

    website_analysis: Dict[str, Any] = field(
        default_factory=dict
    )

    score: float = 0.0
    priority: str = "unknown"

    def to_dict(self):
        return {
            "platform": self.platform,
            "profile_url": self.profile_url,
            "business_name": self.business_name,
            "category": self.category,
            "whatsapp": self.whatsapp,
            "website": self.website,
            "facebook": self.facebook,
            "instagram": self.instagram,
            "ads": self.ads,
            "website_analysis": self.website_analysis,
            "score": self.score,
            "priority": self.priority
        }
