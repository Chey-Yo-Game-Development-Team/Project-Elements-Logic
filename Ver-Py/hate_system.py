"""
Project Elements - Hate & Target System (Phase 3)

実効ヘイト計算とターゲット選定ロジック。
後衛全滅時は生存者の最後尾ポジションを 2.0x に動的繰り上げする。
"""
from __future__ import annotations
from typing import List, Optional

from models import Character, Party, Position

# ポジションの「後ろ度」順序 (大きいほど後ろ)
POSITION_ORDER: dict[Position, int] = {
    Position.FRONT: 0,
    Position.MID: 1,
    Position.BACK: 2,
}


class HateSystem:
    """
    ヘイト管理とターゲット選定を担う静的ユーティリティ。

    動的ポジション補正の考え方:
      「生存者の中で最後尾にいるポジション」は常に 2.0x を得る。
      後衛が全員死んでいれば中衛が 2.0x に繰り上がり、
      中衛まで全滅すれば前衛が 2.0x になる。
    """

    @staticmethod
    def get_dynamic_multiplier(
        character: Character,
        alive_chars: List[Character],
    ) -> float:
        """
        生存者リストを基に動的なポジション補正倍率を返す。

        - 生存者の中で最後尾のポジション → 2.0x（本来の倍率に関わらず）
        - それ以外 → Position に定義された固定倍率
        """
        if not alive_chars:
            return character.position.hate_multiplier

        backmost_order = max(POSITION_ORDER[c.position] for c in alive_chars)
        if POSITION_ORDER[character.position] == backmost_order:
            return 2.0
        return character.position.hate_multiplier

    @classmethod
    def get_effective_hate(
        cls,
        character: Character,
        alive_chars: List[Character],
    ) -> float:
        """実効ヘイトスコア = 基礎ヘイト値 × 動的ポジション補正倍率"""
        return character.base_hate * cls.get_dynamic_multiplier(character, alive_chars)

    @classmethod
    def select_target(cls, characters: List[Character]) -> Optional[Character]:
        """
        生存キャラクターの中から攻撃ターゲットを選択する。

        優先順位:
          1. 実効ヘイトスコアが最大
          2. 同値ならポジションが後ろ（POSITION_ORDER 降順）
          3. さらに同値なら残りHP割合が低い方
        """
        alive = [c for c in characters if c.is_alive]
        if not alive:
            return None

        def sort_key(c: Character):
            hate = cls.get_effective_hate(c, alive)
            return (-hate, -POSITION_ORDER[c.position], c.hp_ratio)

        return min(alive, key=sort_key)

    @staticmethod
    def add_hate(character: Character, amount: float) -> None:
        """行動によるヘイト蓄積（基礎ヘイト値を加算する）。"""
        character.base_hate += amount
