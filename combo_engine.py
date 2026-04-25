"""
Project Elements - Combo Engine (Phase 2)

無属性ジョーカーの自動最適化と属性コンボ判定、ダメージ計算を担う。
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from itertools import product
from typing import List, Tuple

from models import Attribute, Card, Character


# 基本属性のリスト（TYPELESS を除く）
BASIC_ATTRIBUTES = [Attribute.FIRE, Attribute.WATER, Attribute.LIGHT]


class ComboType(Enum):
    FLASH = "flash"       # 同色3枚: 2.5x
    RAINBOW = "rainbow"   # 3色: 1.5x
    PAIR = "pair"         # 同色2枚 + 異色1枚: ペア部分1.2x / 残り1.0x
    NONE = "none"         # 役なし: 1.0x


@dataclass
class ComboResult:
    combo_type: ComboType
    resolved_attributes: List[Attribute]

    def get_multipliers(self) -> List[float]:
        """
        各カード（インデックス順）に対する倍率リストを返す。
        FLASH/RAINBOW は全カード均等倍率、PAIR はペア2枚に1.2x、残り1枚に1.0x。
        """
        if self.combo_type == ComboType.FLASH:
            return [2.5, 2.5, 2.5]
        if self.combo_type == ComboType.RAINBOW:
            return [1.5, 1.5, 1.5]
        if self.combo_type == ComboType.PAIR:
            from collections import Counter
            counts = Counter(self.resolved_attributes)
            pair_attr = max(counts, key=lambda a: counts[a])
            return [1.2 if a == pair_attr else 1.0 for a in self.resolved_attributes]
        return [1.0, 1.0, 1.0]

    @property
    def total_multiplier(self) -> float:
        """コンボ全体の「代表倍率」（FLASH=2.5, RAINBOW=1.5, PAIR=1.2, NONE=1.0）。
        優先度比較に使用する。"""
        priority = {
            ComboType.FLASH: 2.5,
            ComboType.RAINBOW: 1.5,
            ComboType.PAIR: 1.2,
            ComboType.NONE: 1.0,
        }
        return priority[self.combo_type]


def _judge_combo(attrs: List[Attribute]) -> ComboResult:
    """
    3枚の属性リスト（TYPELESS なし）からコンボ役を判定する。
    """
    if len(attrs) != 3:
        raise ValueError(f"カードは3枚必要です（受け取った枚数: {len(attrs)}）")

    unique = set(attrs)

    # フラッシュ: 3枚すべて同属性
    if len(unique) == 1:
        return ComboResult(ComboType.FLASH, attrs)

    # レインボー: 3色すべて揃う
    if unique == set(BASIC_ATTRIBUTES):
        return ComboResult(ComboType.RAINBOW, attrs)

    # ペア: 2種類（2枚 + 1枚）
    if len(unique) == 2:
        return ComboResult(ComboType.PAIR, attrs)

    return ComboResult(ComboType.NONE, attrs)


def resolve_jokers(
    cards: List[Card],
    leader_attribute: Attribute = Attribute.FIRE,
) -> ComboResult:
    """
    手札3枚の TYPELESS（ジョーカー）を最適な基本属性に自動変換してコンボ結果を返す。

    変換の優先順位: FLASH (2.5x) > RAINBOW (1.5x) > PAIR (1.2x) > NONE (1.0x)

    - TYPELESS が 0 枚: そのまま判定。
    - TYPELESS が 1〜2 枚: 全置換パターンを試し最高倍率を選ぶ。
    - TYPELESS が 3 枚: リーダー属性のフラッシュとして扱う。
    """
    if len(cards) != 3:
        raise ValueError(f"カードは3枚必要です（受け取った枚数: {len(cards)}）")

    typeless_indices = [i for i, c in enumerate(cards) if c.attribute == Attribute.TYPELESS]

    # ジョーカーなし
    if not typeless_indices:
        attrs = [c.attribute for c in cards]
        return _judge_combo(attrs)

    # 全3枚がジョーカー
    if len(typeless_indices) == 3:
        resolved = [leader_attribute] * 3
        return ComboResult(ComboType.FLASH, resolved)

    # 1〜2枚がジョーカー: 全置換パターンを列挙して最高役を選ぶ
    base_attrs = [c.attribute for c in cards]
    best: ComboResult | None = None

    replacement_combinations = product(BASIC_ATTRIBUTES, repeat=len(typeless_indices))
    for replacements in replacement_combinations:
        trial = base_attrs[:]
        for idx, replacement in zip(typeless_indices, replacements):
            trial[idx] = replacement
        result = _judge_combo(trial)
        if best is None or result.total_multiplier > best.total_multiplier:
            best = result

    return best  # type: ignore[return-value]  # typeless が 1〜2 枚なら必ず候補がある


@dataclass
class DamageResult:
    character_damages: List[float]
    combo_result: ComboResult

    @property
    def total_damage(self) -> float:
        return sum(self.character_damages)


def calculate_damage(
    cards: List[Card], # プレイされた3枚のカード
    characters: List[Character], # パーティメンバー全員（3体）
    leader_attribute: Attribute = Attribute.FIRE,
) -> DamageResult:
    """
    場にプレイされたカードと、パーティキャラクター全員のステータスから各ダメージを計算する。

    - 属性コンボ倍率（ジョーカー変換済み）を算出し、全キャラクターの基礎攻撃力に乗算する。
    - 所有者一致ボーナス（1.2x）:
      プレイされた3枚のカードの中に、自身の所有するカードが1枚でも含まれているキャラクターの攻撃に適用する。
    - 生存している全キャラクターが攻撃を行う（自身のカードが選ばれなかったキャラもボーナスなしで攻撃する）。

    Args:
        cards: 場にプレイされた3枚のカード
        characters: パーティメンバー全員のリスト（カードとのインデックス同期は不要）
        leader_attribute: 全ジョーカーの場合のフォールバック属性

    Returns:
        各キャラクターが与えるダメージリストとコンボ結果を含む DamageResult
    """
    if len(cards) != 3:
        raise ValueError("プレイされるカードは3枚である必要があります")

    if len(characters) == 0:
        raise ValueError("攻撃を行うキャラクターがパーティに存在しません")

    # 1. コンボ判定と全体倍率の取得
    combo_result = resolve_jokers(cards, leader_attribute)
    combo_multiplier = combo_result.total_multiplier

    # 2. 場に出たカードの所有者（オーナー）をリスト化
    played_owners = [card.owner for card in cards]

    character_damages: List[float] = []

    # 3. 全キャラクターがそれぞれ攻撃を行う
    for char in characters:
        if not char.is_alive:
            character_damages.append(0.0)
            continue

        # 基礎攻撃力 × コンボ全体倍率
        damage = char.attack_power * combo_multiplier

        # 4. 所有者一致ボーナスの判定
        # 場に出た3枚の中に、自分のカードが1枚でもあればボーナス
        if char.name in played_owners:
            damage *= 1.2

        character_damages.append(damage)

    return DamageResult(character_damages=character_damages, combo_result=combo_result)