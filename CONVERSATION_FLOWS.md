# CONVERSATION_FLOWS.md
# تدفقات المحادثة | Conversation Flows & Scripts

---

## Flow 1: Standard Inbound Call (Most Common)

```
CALLER CALLS IN
      │
      ▼
[GREETING]
Agent: "أهلاً وسهلاً، معك مساعد مركز تدريب المحكمة العربية للتحكيم.
        كيف يمكنني مساعدتك اليوم؟"
      │
      ├── "عايز أعرف عن دوراتكم" ──────────────────► [FLOW A: Program Info]
      │
      ├── "عايز أتسجل" / "ابعت لي تفاصيل" ─────────► [FLOW B: Lead Capture]
      │
      ├── "عايز أكلم حد من الفريق" ───────────────► [FLOW C: Human Transfer]
      │
      └── [unclear / silence] ──────────────────────► [FLOW D: Clarification]
```

---

## FLOW A: Program Information

```
Agent: "بنقدم تدريب في عدة مجالات:
        الذكاء الاصطناعي، التمريض، العلاج الطبيعي، وغيرها.
        إيه المجال اللي بتدور عليه؟"

Caller: "الذكاء الاصطناعي"
      │
      ▼
[Info Agent → knowledge_lookup("الذكاء الاصطناعي")]
      │
      ▼
Agent: [reads retrieved info naturally]
"برنامج الذكاء الاصطناعي بيغطي المقدمة في الـ AI وتعلم الآلة،
 وأدوات زي ChatGPT، ومناسب للمبتدئين والمحترفين."

Agent: "هل عندك أي سؤال تاني عن البرنامج ده؟"

Caller: "لأه، كويس"
      │
      ▼
[Transition to Lead Capture]
Agent: "حلو! تفضل أخد بياناتك عشان فريقنا يتواصل معاك بكل التفاصيل؟"
```

---

## FLOW B: Lead Capture

```
Agent: "تمام! هتحتاج بس دقيقتين."

─── Collect Name ───────────────────────────────────────────
Agent: "ممكن أعرف اسمك الكامل؟"
Caller: "أحمد محمد"
Agent: [validates: 2+ words ✓]

─── Collect Phone ──────────────────────────────────────────
Agent: "وما هو رقم تليفونك؟"
Caller: "01012345678"
Agent: [validates: Egyptian format ✓]

  IF invalid:
  Agent: "ممكن تكرر الرقم تاني؟ عشان نتأكد إنه صح."
  IF invalid again:
  Agent: "ممكن تقوله رقم رقم؟"

─── Confirm Program ────────────────────────────────────────
Agent: "وإيه البرنامج اللي بتدور عليه؟"
Caller: "الذكاء الاصطناعي"

─── Confirm All Data ───────────────────────────────────────
Agent: "تمام! هأتأكد من بياناتك:
        اسمك أحمد محمد،
        رقمك 01012345678،
        وبتدور على برنامج الذكاء الاصطناعي.
        هذا صحيح؟"

Caller: "أيوه" / "Yes"
      │
      ▼
[Sheets Writer Agent → google_sheets_append]
      │
      ▼
Agent: "ممتاز! تم تسجيل بياناتك بنجاح.
        هيتواصل معاك فريقنا في أقرب وقت بكل التفاصيل.
        شكراً لتواصلك معنا. مع السلامة!"
```

---

## FLOW C: Human Transfer

```
Agent: "تمام! هحولك دلوقتي لأحد من فريقنا.
        استنى لحظة من فضلك."

[Transfer to: +20XXXXXXXXXX]

  IF no answer:
  Agent: "للأسف الفريق مش متاح دلوقتي.
          هل تقبل نتصل بيك في أقرب وقت؟"
        │
        ▼
  [→ FLOW B: Lead Capture]
```

---

## FLOW D: Clarification

```
Agent: "معلش، مش فاهم كويس.
        هل تريد معلومات عن البرامج، أو تريد التسجيل،
        أو تريد التحدث مع أحد من الفريق؟"

[3 options presented as voice menu]
```

---

## FLOW E: Caller Asks Question Not in Knowledge Base

```
Caller: "كم سعر الدورة؟" [if price not in KB]
      │
      ▼
[Info Agent: knowledge_lookup → confidence < threshold]
      │
      ▼
Agent: "معلومة الأسعار مش متاحة لديّ دلوقتي،
        بس فريقنا هيقدر يوضحلك كل التفاصيل.
        هتقبل نتصل بيك؟"
      │
      ▼
[→ FLOW B: Lead Capture]
```

---

## Sample Full Conversation Script (for testing)

```
AGENT:  أهلاً وسهلاً! معكِ نور من مركز تدريب المحكمة العربية للتحكيم. كيف يمكنني مساعدتك اليوم؟

CALLER: أنا شايف إعلانكم عن دورة التمريض، عايز أعرف أكتر.

AGENT:  نورتنا! برنامج التمريض عندنا شامل جداً، مدته سنة كاملة (9 شهور نظري و3 شهور عملي)، وبيغطي كل حاجة من أول المهارات الأساسية لحد الإسعافات والطوارئ.
        البرنامج معتمد بشهادة بختم النسر من وزارة الخارجية.
        وضحت لحضرتك الصورة؟ أو حابب تسأل عن حاجة تانية؟

CALLER: تمام. إيه الأسعار؟

AGENT:  السعر الإجمالي للكورس 15,000 جنيه مصري شامل كل شيء، ومفيش أي مصاريف إضافية.
        وعندنا نظام تقسيط مريح: 3,000 جنيه مقدم والباقي على 6 شهور.
        تحب نعرف أكتر عن نظام التقسيط؟

CALLER: أيوه تمام.

AGENT:  ممتاز! عشان نقدر نبعتلك كل التفاصيل الرسمية وصور الاعتمادات، ممكن آخد بياناتك في دقيقتين؟

CALLER: أيوه تمام.

AGENT:  ممكن اسمك الكامل من فضلك؟

CALLER: سارة إبراهيم

AGENT:  ورقم تليفونك؟

CALLER: 01098765432

AGENT:  وبتدوري على برنامج التمريض صح؟

CALLER: أيوه.

AGENT:  تمام! هأتأكد من بياناتك: اسمك سارة إبراهيم، رقمك 01098765432، وبتدوري على كورس التمريض المعتمد. هذا صحيح؟

CALLER: أيوه صح.

AGENT:  ممتاز! بسجل بياناتك دلوقتي... تم التسجيل بنجاح وفريقنا هيتواصل معاك قريباً جداً.
        نورتينا يا سارة. مع السلامة!

[END CALL]
[→ Sheets row appended: timestamp | سارة إبراهيم | 01098765432 | التمريض | summary...]
```

---

## Error Handling Scripts

### Google Sheets write failure:
```
Agent: "معلش في مشكلة تقنية صغيرة.
        ممكن تتصلي بينا تاني؟ أو فريقنا هيتواصل معاك مباشرة."
```

### Call drops mid-capture:
```
[System saves partial state]
[Flag for manual follow-up in error queue]
```

### Caller hangs up before confirmation:
```
[Do NOT write to Sheets – data not confirmed]
[Log as incomplete_lead in error queue]
```
