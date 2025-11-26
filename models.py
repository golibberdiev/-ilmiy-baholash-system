from typing import List, Dict, Literal, Optional

from pydantic import BaseModel, Field, validator

from sqlalchemy import Column, Integer, String, Float, JSON
from db import Base


# ===========================
#  Pydantic ma'lumot modellar
# ===========================

class Indicator(BaseModel):
    """
    Bitta ilmiy ko‘rsatkich modeli.
    Masalan:
      - R1: Ilmiy darajali xodimlar ulushi
      - O1: Scopusdagi maqolalar soni
      - I1: Tijoratlashtirilgan ishlanmalar soni
    """
    id: str
    name: str
    block: Literal["R", "P", "O", "I"]
    value: float
    min_value: float
    max_value: float
    weight: float = Field(ge=0, le=1, description="Ko‘rsatkichning vazn koeffitsiyenti (0..1)")
    is_benefit: bool = True  # True bo‘lsa – ko‘rsatkich yuqori bo‘lgani yaxshi

    @validator("max_value")
    def check_min_max(cls, v, values):
        """
        min_value va max_value mantiqan to‘g‘ri kiritilganligini tekshiradi.
        """
        min_v = values.get("min_value")
        if min_v is not None and v <= min_v:
            raise ValueError("max_value min_value dan katta bo‘lishi kerak")
        return v


class BlockWeights(BaseModel):
    """
    R, P, O, I bloklarining og‘irlik koeffitsiyentlari.
    Hozircha default qiymatlar 0.25 dan teng olinyapti.
    """
    alpha_R: float = 0.25
    alpha_P: float = 0.25
    alpha_O: float = 0.25
    alpha_I: float = 0.25

    @validator("alpha_R", "alpha_P", "alpha_O", "alpha_I")
    def check_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Blok og‘irliklari manfiy bo‘lmasligi kerak")
        return v

    @property
    def total(self) -> float:
        """
        Foydali qo‘shimcha: og‘irliklar yig‘indisini qaytaradi.
        """
        return self.alpha_R + self.alpha_P + self.alpha_O + self.alpha_I


class EvaluationRequest(BaseModel):
    """
    /evaluate endpointiga keladigan so‘rov modeli:
      - tashkilot (ixtiyoriy)
      - yil (ixtiyoriy)
      - indicators: ko‘rsatkichlar ro‘yxati
      - block_weights: blok og‘irliklari
    """
    tashkilot: Optional[str] = None
    yil: Optional[int] = None
    indicators: List[Indicator]
    block_weights: BlockWeights


class BlockIndex(BaseModel):
    """
    Bitta blok (R, P, O yoki I) bo‘yicha integral indeks.
      - block: blok kodi
      - value: blok uchun hisoblangan indeks (0..1 oralig‘ida)
      - indicators: shu blokdagi ko‘rsatkichlarning normallashtirilgan qiymatlari
    """
    block: Literal["R", "P", "O", "I"]
    value: float
    indicators: Dict[str, float]


class EvaluationResult(BaseModel):
    """
    Hisoblash natijasi:
      - total_index: tashkilotning integral ilmiy samaradorlik indeksi
      - blocks: R, P, O, I bloklari bo‘yicha indekslar
      - level, weakest_block, strongest_block: keyingi bosqichda
        algoritmni boyitish uchun ishlatiladigan qo‘shimcha maydonlar.
        Hozircha ular ixtiyoriy (Optional) qilib qo‘yildi,
        shuning uchun mavjud core.py bilan ham mos ishlaydi.
    """
    tashkilot: Optional[str] = None
    yil: Optional[int] = None
    total_index: float
    blocks: List[BlockIndex]

    # Kelajakda core.py yangilanganida to‘ldirilishi mumkin bo‘lgan maydonlar:
    level: Optional[str] = None            # masalan: "Past", "O‘rtacha", "Yuqori", "Juda yuqori"
    weakest_block: Optional[str] = None    # "R", "P", "O" yoki "I"
    strongest_block: Optional[str] = None  # "R", "P", "O" yoki "I"


# ===========================
#  SQLAlchemy ORM modeli
# ===========================

class Evaluation(Base):
    """
    Ma'lumotlar bazasida saqlanadigan baholash yozuvi.
    Jadval nomi: evaluations

    Maydonlar:
      - id: birlamchi kalit
      - tashkilot: tashkilot nomi
      - yil: baholash yili
      - total_index: umumiy indeks S
      - block_values: JSON ko‘rinishida blok indekslari, masalan:
            {"R": 0.45, "P": 0.62, "O": 0.71, "I": 0.38}
    """
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    tashkilot = Column(String, index=True)
    yil = Column(Integer, index=True)
    total_index = Column(Float)
    block_values = Column(JSON)  # {"R":0.25, "P":0.5, "O":0.7, "I":0.3}

    def __repr__(self) -> str:
        return (
            f"<Evaluation id={self.id} tashkilot={self.tashkilot!r} "
            f"yil={self.yil} total_index={self.total_index}>"
        )
