class OfferGenerator:
    def generate(self, lead):
        business = lead.get("business", {})
        name = business.get("name", "حضرتك")

        ads = lead.get("ads", {})
        website = lead.get("website", {})

        running_ads = ads.get("running", False)
        ad_count = ads.get("creative_count", 0)

        cta = website.get("cta", {}).get("detected", False)
        tracking = website.get("tracking", {}).get("detected", [])
        whatsapp = website.get("contact", {}).get("whatsapp", False)

        problems = []

        if running_ads and not cta:
            problems.append(
                "الإعلانات شغالة لكن الـLanding Page مفيهاش CTA واضح"
            )

        if running_ads and not tracking:
            problems.append(
                "فيه إعلانات لكن الـtracking الظاهر محدود، وده يصعّب قياس الـROAS"
            )

        if running_ads and ad_count > 0:
            problems.append(
                f"فيه نشاط إعلاني ظاهر ({ad_count} creative)"
            )

        if not whatsapp:
            problems.append(
                "الـWebsite مش موضح فيه مسار WhatsApp مباشر"
            )

        if not problems:
            problems.append(
                "فيه فرصة لتحسين الـMedia Buying والـconversion funnel"
            )

        message = (
            f"أهلًا {name}،\n\n"
            f"بصيت على الـFacebook/Instagram والحضور الإعلاني "
            f"والـWebsite عندكم، ولاحظت كام نقطة ممكن يكون لها تأثير "
            f"مباشر على نتيجة الـMedia Buying:\n\n"
        )

        message += "\n".join(
            f"• {problem}"
            for problem in problems[:4]
        )

        message += (
            "\n\nأنا شغلي مش مجرد تشغيل Ads؛ "
            "الهدف إننا نربط الـMedia Buying بالـTracking والـLanding Page "
            "بحيث نعرف بالضبط إيه اللي بيجيب Leads ومبيعات.\n\n"
            "لو مناسب، أقدر أعمل لكم مراجعة سريعة للحملات الحالية "
            "وأقولكم أهم 3 حاجات أبدأ بيها."
        )

        return {
            "message": message,
            "problems": problems,
            "signals": {
                "running_ads": running_ads,
                "creative_count": ad_count,
                "has_cta": cta,
                "tracking": tracking,
                "has_whatsapp": whatsapp
            }
        }
