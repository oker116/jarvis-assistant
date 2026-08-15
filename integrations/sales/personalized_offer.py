import json


class PersonalizedOfferGenerator:

    STYLES = [
        "direct",
        "casual",
        "problem_solution",
        "curiosity",
        "audit",
    ]

    def _choose_style(self, requested=None, lead_id=None):
        if requested in self.STYLES:
            return requested

        # First preference: a style that has demonstrated
        # enough real-world performance.
        try:
            from integrations.sales.conversation_learning import (
                ConversationLearning
            )

            learning = ConversationLearning()

            best = learning.best_offer_style(
                minimum_observations=3
            )

            if best and best.get("style") in self.STYLES:
                return best["style"]

        except Exception:
            pass

        # Exploration phase:
        # deliberately rotate styles instead of sending
        # the same copy every time.
        seed = str(lead_id or "unknown")

        index = sum(
            ord(char) for char in seed
        ) % len(self.STYLES)

        return self.STYLES[index]

    def _facts(self, analysis):
        signals = analysis.get("signals") or []
        opportunities = analysis.get("opportunities") or []

        return signals[:4], opportunities[:3]

    def _arabic_fact(self, fact):
        translations = {
            "Active Facebook presence detected.":
                "واضح إن عندكم نشاط كويس على فيسبوك.",
            "Recent Facebook activity detected.":
                "واضح إن الصفحة عندكم عليها نشاط مستمر.",
            "Large Facebook audience.":
                "عندكم قاعدة جمهور كويسة على فيسبوك.",
            "Established Facebook audience.":
                "عندكم جمهور موجود بالفعل على فيسبوك.",
            "Growing Facebook audience.":
                "واضح إن جمهور الصفحة في نمو.",
            "Active paid advertising detected.":
                "واضح إنكم شغالين حاليًا على إعلانات مدفوعة.",
            "Historical advertising activity detected.":
                "واضح إن كان عندكم نشاط إعلاني قبل كده.",
            "Limited creative variation.":
                "في فرصة لاختبار تنوع أكبر في الـCreatives.",
            "Business website detected.":
                "عندكم Website شغال وموجود ضمن رحلة العميل.",
            "Website has a visible conversion CTA.":
                "الـWebsite عنده CTA واضح للزائر.",
            "Tracking technology detected.":
                "في Tracking موجود نقدر نبني عليه.",
            "Commercial offer detected.":
                "واضح إن عندكم عرض تجاري ممكن يتبني عليه في الإعلانات.",
            "Business WhatsApp contact detected.":
                "وWhatsApp موجود كقناة تواصل مع العملاء.",
        }

        return translations.get(fact)

    def _translate_opportunity(self, item):
        translations = {
            "Campaign optimization opportunity.":
                "تحسين أداء الحملات الحالية.",
            "Creative testing opportunity.":
                "اختبار Creatives وزوايا مختلفة.",
            "Tracking setup should be reviewed.":
                "مراجعة الـTracking عشان نعرف الإعلان اللي بيجيب نتيجة فعلًا.",
            "Landing page optimization opportunity.":
                "تحسين الـLanding Page عشان نسبة التحويل.",
            "Website CTA optimization opportunity.":
                "تحسين الـCTA داخل الـWebsite.",
        }

        return translations.get(item)

    def generate(
        self,
        lead,
        analysis,
        research=None,
        style=None,
    ):
        research = research or {}

        name = lead.get("name") or "حضرتك"
        score = float(
            analysis.get("score")
            or lead.get("score")
            or 0
        )

        service = (
            analysis.get("recommended_service")
            or "Media Buying Audit + Campaign Optimization"
        )

        signals, opportunities = self._facts(
            analysis
        )

        facts = [
            self._arabic_fact(x)
            for x in signals
        ]

        facts = [
            x for x in facts if x
        ]

        problems = [
            self._translate_opportunity(x)
            for x in opportunities
        ]

        problems = [
            x for x in problems if x
        ]

        selected_style = self._choose_style(
            requested=style,
            lead_id=lead.get("lead_id")
        )

        # -------------------------------
        # STYLE 1: DIRECT
        # -------------------------------
        if selected_style == "direct":

            body = (
                f"أهلًا {name} 👋\n\n"
                "بصيت بسرعة على النشاط التسويقي عندكم، "
                "ولاحظت كام فرصة ممكن تستاهل تتراجع:\n\n"
                + "\n".join(
                    f"• {x}" for x in facts[:3]
                )
                + "\n\n"
                + (
                    "أكتر نقطة لفتت نظري: "
                    + problems[0]
                    + "\n\n"
                    if problems else ""
                )
                + "إحنا بنشتغل على تحسين الـMedia Buying "
                "والـTracking بحيث الميزانية تروح للحاجات "
                "اللي بتجيب نتيجة فعلية.\n\n"
                "لو حابب، أقدر أبعتلك Audit سريع "
                "وأقولك أبدأ منين."
            )

        # -------------------------------
        # STYLE 2: CASUAL
        # -------------------------------
        elif selected_style == "casual":

            body = (
                f"أهلًا {name}، عاملين إيه؟ 👋\n\n"
                "دخلت أبص على الـMarketing عندكم شوية، "
                "ولقيت إن عندكم أساس كويس نقدر نشتغل عليه.\n\n"
                + "\n".join(
                    f"• {x}" for x in facts[:2]
                )
                + "\n\n"
                + (
                    "وفيه فرصة واضحة في "
                    + problems[0]
                    + ".\n\n"
                    if problems else ""
                )
                + "مش هطول عليك، لو تحب أبص على الحملات "
                "وأقولك فين أسرع فرصة للتحسين، أعملهالك "
                "في مراجعة بسيطة."
            )

        # -------------------------------
        # STYLE 3: PROBLEM / SOLUTION
        # -------------------------------
        elif selected_style == "problem_solution":

            body = (
                f"أهلًا {name}.\n\n"
                "في حاجة لفتت نظري وأنا براجع النشاط "
                "الإعلاني عندكم.\n\n"
                + (
                    "• " + problems[0] + "\n\n"
                    if problems else ""
                )
                + "وده مهم لأن تشغيل Ads لوحده مش كفاية؛ "
                "المهم نعرف العميل جه منين وإيه اللي "
                "بيحوّله لعميل فعلي.\n\n"
                "أقدر أعمل مراجعة للحملات والـTracking "
                "وأطلعلك أهم 3 نقاط محتاجة تعديل."
            )

        # -------------------------------
        # STYLE 4: CURIOSITY
        # -------------------------------
        elif selected_style == "curiosity":

            body = (
                f"أهلًا {name} 👋\n\n"
                "وأنا براجع الـMarketing عندكم، "
                "لقيت نقطة معينة ممكن تكون مؤثرة "
                "على نتيجة الإعلانات.\n\n"
                + (
                    "خصوصًا موضوع "
                    + problems[0]
                    + ".\n\n"
                    if problems else ""
                )
                + "مش عايز أفترض حاجة من بره، "
                "بس لو تحب أبص على الـCampaign setup "
                "وأقولك إيه اللي شايفه، أقدر أعمل "
                "مراجعة سريعة جدًا."
            )

        # -------------------------------
        # STYLE 5: AUDIT
        # -------------------------------
        else:

            body = (
                f"أهلًا {name}.\n\n"
                "عملت Review مبدئي للحضور الرقمي والإعلاني "
                "عندكم.\n\n"
                + "\n".join(
                    f"• {x}" for x in facts[:3]
                )
                + "\n\n"
                "وبناءً على اللي ظهر، شايف إن أنسب بداية "
                "هي Media Buying Audit + Campaign Optimization.\n\n"
                "الفكرة مش مجرد تشغيل إعلانات؛ "
                "نحدد الأول فين التسريب في الـFunnel "
                "وإيه اللي محتاج يتظبط في الـTracking "
                "والـCampaigns.\n\n"
                "لو مناسب، أبعتلك ملخص الـAudit."
            )

        return {
            "lead_id": lead.get("lead_id"),
            "name": name,
            "score": score,
            "service": service,
            "evidence": facts,
            "pain_points": problems,
            "style": selected_style,
            "message": body,
            "mode": "OUTREACH_ONLY",
            "auto_reply": False,
        }


if __name__ == "__main__":

    generator = PersonalizedOfferGenerator()

    lead = {
        "lead_id": "demo",
        "name": "Test Restaurant",
        "score": 79,
    }

    analysis = {
        "score": 79,
        "signals": [
            "Active paid advertising detected.",
            "Established Facebook audience.",
            "Business website detected.",
            "Business WhatsApp contact detected.",
        ],
        "opportunities": [
            "Campaign optimization opportunity.",
            "Tracking setup should be reviewed.",
        ],
        "recommended_service":
            "Media Buying Audit + Campaign Optimization",
    }

    for style in generator.STYLES:

        result = generator.generate(
            lead,
            analysis,
            style=style
        )

        print("\n" + "=" * 60)
        print("STYLE:", style)
        print("=" * 60)
        print(result["message"])
