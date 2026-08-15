# -*- coding: cp1256 -*-

class Decision:

    def __init__(self):
        self.intent = "unknown"
        self.confidence = 0.0
        self.reason = ""

    def analyze(self, text):

        text = text.strip().lower()

        self.intent = "conversation"
        self.confidence = 0.50
        self.reason = "طلب عام."

        if "حلل" in text or "تحليل" in text:
            self.intent = "analysis"
            self.confidence = 0.90
            self.reason = "المستخدم يطلب تحليلًا."

        elif "تعلم" in text or "احفظ" in text:
            self.intent = "learning"
            self.confidence = 0.90
            self.reason = "المستخدم يريد إضافة معرفة."

        elif "افتح" in text or "شغل" in text:
            self.intent = "action"
            self.confidence = 0.85
            self.reason = "المستخدم يطلب تنفيذ إجراء."

        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "reason": self.reason
        }