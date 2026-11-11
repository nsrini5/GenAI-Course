# 7-Day Vegetarian South Indian Meal Plan — Gluten-Free Version (RTCFR)

> **Same prompt as `meal_plan_prompt.md`, with a gluten allergy in the PROFILE** and gluten rules
> added to CONTEXT and the few-shot examples.
>
> **How to use:** edit only the **PROFILE** block, then copy everything below the line into any AI
> chat tool (ChatGPT, Claude, Gemini, or `ollama run qwen2.5`). The output is a draft to think
> about, not dietary advice — a real plan belongs with a qualified dietitian.

---

## ✏️ PROFILE — the only block you edit (feeds the CONTEXT section)

```
Person:               51-year-old man
Height / weight:      173 cm / 114 kg
Goal:                 gradual weight loss (about 0.5 kg a week)
Activity level:       sedentary desk job, 30-minute walk 5 days a week
Allergies:            gluten - no wheat, rava/sooji, semiya (vermicelli), maida,
                      barley or rye, in any form
Dislikes:             pumpkin
Region / cuisine:     Tamil Nadu home cooking
Season / month:       November (north-east monsoon)
Weekday cooking time: 20 minutes for breakfast, 40 minutes for dinner
Who eats together:    only on Sundays
Lunch:                packed tiffin carried to work, Monday to Saturday
Dairy:                curd, buttermilk, milk and paneer are fine
Budget:               everyday middle-class household
```

---

## R — ROLE

You are an experienced Indian clinical nutritionist who plans everyday South Indian home food
for weight loss. You write for ordinary households, not athletes, and you only use dishes a home
cook in the PROFILE region already knows how to make.

## T — TASK

Create a **7-day vegetarian South Indian meal plan** (Monday to Sunday) for the person in the
PROFILE, supporting gradual weight loss. Each day has exactly **four meals in this order:
Breakfast, Lunch, Snack, Dinner** — 28 meals in total. Every meal must name a real dish and give
a portion size.

## C — CONTEXT

**Who it is for:** the person described in the PROFILE block. Respect every detail of it —
activity level, allergies, dislikes, region, season, cooking time, who eats together and the lunch
arrangement.

**Rules the plan must follow:**

1. **Vegetarian only** — no meat, fish or egg. Dairy only as the PROFILE allows.
2. **Recognisably South Indian** — real dishes such as *ragi dosa*, *keerai kootu*, *sundal*,
   *pongal*, *kambu koozh*; never generic phrases like "a healthy breakfast".
3. **Local and seasonal** — ingredients sold in an ordinary local market in the PROFILE region and
   month. Millets (ragi, kambu, thinai, varagu, samai) are welcome.
4. **Balanced meals** — every main meal has a protein (dal, sambar, sundal, curd, paneer, legumes),
   a vegetable and a measured portion of cereal or millet.
5. **No extreme restriction** — a moderate deficit only (roughly 1,500–1,800 kcal a day for an
   adult, never below 1,200). No fasting days, skipped meals, detox or single-food days.
6. **Practical** — weekday breakfast and dinner fit the PROFILE cooking times; batch items
   (dosa batter, sambar, chutney) may be reused across days. Packed lunches must travel well.
7. **Variety** — no main dish more than twice in the week; rice at most once a day.
8. **Oil and salt** — at most 3–4 teaspoons of oil per person per day; no deep-fried food except
   one small weekend treat portion.
9. **Never include** an allergen or a disliked food, not even as a garnish or in a side dish.
10. **Gluten-free throughout.** No wheat, chapati, wheat dosa, rava or sooji (upma, rava dosa,
    kesari), semiya / vermicelli, maida, bread, biscuits, barley or rye. Build meals on rice,
    idli/dosa batter (rice + urad dal), millets (ragi, kambu, thinai, varagu, samai, jowar),
    dals and legumes. Season with **gluten-free asafoetida** only, as ordinary hing is often
    mixed with wheat flour, and avoid ready mixes and appalam unless the label says gluten-free.

**Do not use:** quinoa, avocado, kale, chia seeds, broccoli bowls, smoothie bowls, Greek yoghurt,
Western-style oats porridge, protein powder, supplements, meal-replacement shakes, detox drinks,
keto or crash-diet framing, words like *cheat meal* / *guilt-free* / *burn fat fast* / *superfood*,
or any medical claim or promised weight loss.

## F — FEW-SHOT EXAMPLES

These show the **style and level of detail** expected. They are not part of the plan — do not copy
these dishes; build the week from the PROFILE.

**Good rows (follow this pattern):**

| Day | Meal | Dish | Portion |
|---|---|---|---|
| Mon | Breakfast | Idli with sambar and coconut chutney | 3 idli (≈150 g) + 1 katori sambar (150 ml) + 2 tbsp chutney |
| Mon | Lunch | Brown rice, beans poriyal, moong dal kootu, curd | ¾ cup cooked rice (≈120 g) + 1 katori poriyal + 1 katori kootu + ½ cup curd |
| Mon | Snack | Kondakadalai (chickpea) sundal with buttermilk | ½ cup sundal (≈60 g) + 1 glass buttermilk (200 ml) |
| Mon | Dinner | Ragi dosa with tomato chutney and keerai masiyal | 2 dosa (≈120 g) + 2 tbsp chutney + 1 katori keerai |

**Bad rows (never write like this):**

| Day | Meal | Dish | Portion |
|---|---|---|---|
| Mon | Breakfast | A healthy breakfast | Small bowl |
| Mon | Lunch | Quinoa salad with avocado | As needed |
| Mon | Dinner | Chapati with kurma (contains wheat) | 2 chapati |

## R — RESPONSE FORMAT

1. Output **one Markdown table only**, with exactly these columns: `| Day | Meal | Dish | Portion |`
2. `Day` = Mon, Tue, Wed, Thu, Fri, Sat, Sun. `Meal` = Breakfast, Lunch, Snack or Dinner, in that order.
3. `Dish` = dish name(s) in English letters, with sides.
4. `Portion` = household measures (pieces, cups, katori, tbsp, glass) **plus** approximate grams or ml.
5. Exactly **28 rows** — no merged meals, no "same as Monday".
6. After the table, at most **three short lines**: one on how the plan fits the PROFILE, and this
   line: *"This is a draft for discussion, not medical advice; please consult a qualified dietitian."*
7. No introduction, headings, calorie tables, recipes or long explanations.

**Before you answer, check:** 28 rows · nothing that contains gluten · every dish vegetarian and South Indian with a portion ·
nothing from "Do not use" · no allergen or disliked food · no main dish more than twice.
