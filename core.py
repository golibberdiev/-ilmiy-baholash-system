from typing import Dict, List

from models import Indicator, BlockIndex, EvaluationRequest, EvaluationResult


# ===========================
#  Yordamchi funksiyalar
# ===========================

def normalize(ind: Indicator) -> float:
    """
    Ko‘rsatkich qiymatini [0; 1] oraliqqa keltirish.

    Foydalanilayotgan formula:
        z = (value - min_value) / (max_value - min_value)

    Agar ko‘rsatkich "cost" (ya'ni past bo‘lgani yaxshi) bo‘lsa,
    is_benefit = False beriladi va z = 1 - z shaklida o‘zgartiriladi.

    Natija har doim 0 va 1 oralig‘ida bo‘lishi uchun cheklanadi.
    """
    if ind.max_value == ind.min_value:
        # Degeneratsiya holati: min va max bir xil bo‘lsa,
        # normalizatsiya ma'nosiz – 0 deb olinadi.
        return 0.0

    z = (ind.value - ind.min_value) / (ind.max_value - ind.min_value)

    # Agar ko‘rsatkich "foyda emas" bo‘lsa (cost), teskarisiga olamiz
    if not ind.is_benefit:
        z = 1 - z

    # 0..1 oralig‘ida cheklab qo‘yish
    return max(0.0, min(1.0, z))


def classify_level(total_index: float) -> str:
    """
    Umumiy integral indeksni sifat darajalariga ajratish.

    Diapazonlar (dissertatsiya uchun qulay):

      0.00 – 0.25  ->  "Past"
      0.25 – 0.50  ->  "O‘rtacha"
      0.50 – 0.75  ->  "Yuqori"
      0.75 – 1.00  ->  "Juda yuqori"
    """
    if total_index < 0.25:
        return "Past"
    elif total_index < 0.50:
        return "O‘rtacha"
    elif total_index < 0.75:
        return "Yuqori"
    else:
        return "Juda yuqori"


# ===========================
#  Asosiy baholash funksiyasi
# ===========================

def evaluate(req: EvaluationRequest) -> EvaluationResult:
    """
    Tashkilotning ilmiy faoliyati samaradorligini baholash.

    Kirish:
      - req.indicators: ko‘rsatkichlar ro‘yxati (R, P, O, I bloklari bo‘yicha)
      - req.block_weights: bloklar og‘irliklari (alpha_R, alpha_P, alpha_O, alpha_I)

    Chiqish:
      - EvaluationResult:
          * total_index – integral indeks
          * blocks – blok indekslari
          * level – sifat darajasi (Past, O‘rtacha, ...)
          * weakest_block / strongest_block – eng zaif va eng kuchli bloklar
    """

    # 1. Ko‘rsatkichlarni bloklar bo‘yicha guruhlash
    block_groups: Dict[str, List[Indicator]] = {"R": [], "P": [], "O": [], "I": []}

    for ind in req.indicators:
        if ind.block not in block_groups:
            # Noto‘g‘ri blok kodi kiritilgan holat
            raise ValueError(f"Noma'lum blok kodi: {ind.block}")
        block_groups[ind.block].append(ind)

    block_indices: List[BlockIndex] = []
    block_values: Dict[str, float] = {}

    # 2. Har bir blok uchun vaznlangan indeksni hisoblash
    for block_code, indicators in block_groups.items():
        if not indicators:
            # Agar blok bo‘yicha ko‘rsatkich bo‘lmasa – indeks 0
            block_values[block_code] = 0.0
            block_indices.append(
                BlockIndex(block=block_code, value=0.0, indicators={})
            )
            continue

        norm_values: Dict[str, float] = {}
        block_sum = 0.0
        weight_sum = 0.0

        for ind in indicators:
            z = normalize(ind)
            norm_values[ind.id] = z
            block_sum += z * ind.weight
            weight_sum += ind.weight

        block_index_value = block_sum / weight_sum if weight_sum > 0 else 0.0
        block_values[block_code] = block_index_value

        block_indices.append(
            BlockIndex(
                block=block_code,
                value=round(block_index_value, 3),
                indicators=norm_values,
            )
        )

    # 3. Blok og‘irliklari asosida umumiy indeksni hisoblash
    bw = req.block_weights

    total_index_raw = (
        bw.alpha_R * block_values.get("R", 0.0)
        + bw.alpha_P * block_values.get("P", 0.0)
        + bw.alpha_O * block_values.get("O", 0.0)
        + bw.alpha_I * block_values.get("I", 0.0)
    )

    total_index = round(total_index_raw, 3)

    # 4. Sifat darajasi (klassifikatsiya)
    level = classify_level(total_index)

    # 5. Eng kuchli va eng zaif bloklarni aniqlash
    #    (faqat haqiqatan mavjud bloklar bo‘yicha)
    if block_values:
        weakest_block = min(block_values, key=block_values.get)
        strongest_block = max(block_values, key=block_values.get)
    else:
        weakest_block = ""
        strongest_block = ""

    # 6. Natijani qaytarish
    return EvaluationResult(
        tashkilot=req.tashkilot,
        yil=req.yil,
        total_index=total_index,
        blocks=block_indices,
        level=level,
        weakest_block=weakest_block or None,
        strongest_block=strongest_block or None,
    )
