"""
Project Elements - Combo Engine Unit Tests (Phase 2)

仕様書 §2 「属性コンボシステム」および無属性ジョーカー最適化ロジックを検証する。
"""
import pytest
from models import Attribute, Card, Character, Position
from combo_engine import (
    ComboType,
    ComboResult,
    resolve_jokers,
    calculate_damage,
    _judge_combo,
)

# ---------------------------------------------------------------------------
# テスト用ヘルパー
# ---------------------------------------------------------------------------

def make_cards(*attrs: Attribute, power: float = 10.0):
    """属性リストからカードリストを生成する。"""
    return [Card(a, power) for a in attrs]


def make_char(attr: Attribute, position: Position = Position.MID) -> Character:
    """テスト用キャラクターを生成する（カードは3枚のダミーで固定）。"""
    cards = [Card(attr, 10.0)] * 3
    return Character(name="test", attribute=attr, max_hp=100, position=position, cards=cards)


# ---------------------------------------------------------------------------
# §2-2: コンボ役判定（ジョーカーなし）
# ---------------------------------------------------------------------------

class TestJudgeCombo:
    def test_flash_same_three(self):
        attrs = [Attribute.FIRE, Attribute.FIRE, Attribute.FIRE]
        result = _judge_combo(attrs)
        assert result.combo_type == ComboType.FLASH

    def test_flash_water(self):
        attrs = [Attribute.WATER, Attribute.WATER, Attribute.WATER]
        result = _judge_combo(attrs)
        assert result.combo_type == ComboType.FLASH

    def test_rainbow_all_three(self):
        attrs = [Attribute.FIRE, Attribute.WATER, Attribute.LIGHT]
        result = _judge_combo(attrs)
        assert result.combo_type == ComboType.RAINBOW

    def test_rainbow_order_irrelevant(self):
        attrs = [Attribute.WATER, Attribute.LIGHT, Attribute.FIRE]
        result = _judge_combo(attrs)
        assert result.combo_type == ComboType.RAINBOW

    def test_pair_fire_fire_water(self):
        attrs = [Attribute.FIRE, Attribute.FIRE, Attribute.WATER]
        result = _judge_combo(attrs)
        assert result.combo_type == ComboType.PAIR

    def test_pair_multipliers_position(self):
        """ペアのカード倍率: ペア2枚=1.2x, 残り1枚=1.0x"""
        attrs = [Attribute.FIRE, Attribute.FIRE, Attribute.WATER]
        result = _judge_combo(attrs)
        mults = result.get_multipliers()
        assert mults[0] == 1.2
        assert mults[1] == 1.2
        assert mults[2] == 1.0

    def test_invalid_card_count(self):
        with pytest.raises(ValueError):
            _judge_combo([Attribute.FIRE, Attribute.FIRE])


# ---------------------------------------------------------------------------
# §2-3: ジョーカー変換ロジック
# ---------------------------------------------------------------------------

class TestResolveJokers:
    # --- 無属性なし ---
    def test_no_typeless(self):
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.FIRE)
        result = resolve_jokers(cards)
        assert result.combo_type == ComboType.FLASH

    # --- 仕様書ケース: [火, 火, 無] → フラッシュ ---
    def test_one_typeless_to_flash(self):
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.TYPELESS)
        result = resolve_jokers(cards)
        assert result.combo_type == ComboType.FLASH

    # --- 仕様書ケース: [火, 水, 無] → レインボー（ペアより優先） ---
    def test_one_typeless_to_rainbow_over_pair(self):
        cards = make_cards(Attribute.FIRE, Attribute.WATER, Attribute.TYPELESS)
        result = resolve_jokers(cards)
        assert result.combo_type == ComboType.RAINBOW

    # --- 仕様書ケース: [火, 無, 無] → フラッシュ ---
    def test_two_typeless_to_flash(self):
        cards = make_cards(Attribute.FIRE, Attribute.TYPELESS, Attribute.TYPELESS)
        result = resolve_jokers(cards)
        assert result.combo_type == ComboType.FLASH

    # --- 仕様書ケース: [無, 無, 無] → リーダー属性のフラッシュ ---
    def test_all_typeless_uses_leader(self):
        cards = make_cards(Attribute.TYPELESS, Attribute.TYPELESS, Attribute.TYPELESS)
        result = resolve_jokers(cards, leader_attribute=Attribute.WATER)
        assert result.combo_type == ComboType.FLASH
        assert all(a == Attribute.WATER for a in result.resolved_attributes)

    def test_all_typeless_default_leader_fire(self):
        cards = make_cards(Attribute.TYPELESS, Attribute.TYPELESS, Attribute.TYPELESS)
        result = resolve_jokers(cards)  # デフォルトは FIRE
        assert result.combo_type == ComboType.FLASH
        assert all(a == Attribute.FIRE for a in result.resolved_attributes)

    # --- 残った1ジョーカーが光に変換されレインボー ---
    def test_one_typeless_resolved_to_light(self):
        cards = make_cards(Attribute.FIRE, Attribute.WATER, Attribute.TYPELESS)
        result = resolve_jokers(cards)
        assert Attribute.LIGHT in result.resolved_attributes

    # --- ジョーカー2枚: [水, 無, 無] → フラッシュ(水) ---
    def test_two_typeless_water_flash(self):
        cards = make_cards(Attribute.WATER, Attribute.TYPELESS, Attribute.TYPELESS)
        result = resolve_jokers(cards)
        assert result.combo_type == ComboType.FLASH
        assert all(a == Attribute.WATER for a in result.resolved_attributes)


# ---------------------------------------------------------------------------
# §2-2: コンボ倍率の正確な値
# ---------------------------------------------------------------------------

class TestComboMultipliers:
    def test_flash_multiplier(self):
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.FIRE)
        result = resolve_jokers(cards)
        assert result.total_multiplier == 2.5
        assert result.get_multipliers() == [2.5, 2.5, 2.5]

    def test_rainbow_multiplier(self):
        cards = make_cards(Attribute.FIRE, Attribute.WATER, Attribute.LIGHT)
        result = resolve_jokers(cards)
        assert result.total_multiplier == 1.5
        assert result.get_multipliers() == [1.5, 1.5, 1.5]

    def test_pair_priority_multiplier(self):
        """ペア代表倍率は 1.2"""
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.WATER)
        result = resolve_jokers(cards)
        assert result.total_multiplier == 1.2


# ---------------------------------------------------------------------------
# §2-4: ダメージ計算（属性一致ボーナス）
# ---------------------------------------------------------------------------

class TestCalculateDamage:
    def test_flash_no_bonus(self):
        """フラッシュ成立 + 属性不一致: 10 * 2.5 = 25.0 x3"""
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.FIRE, power=10.0)
        chars = [make_char(Attribute.WATER)] * 3
        result = calculate_damage(cards, chars)
        assert result.total_damage == pytest.approx(75.0)

    def test_flash_with_bonus(self):
        """フラッシュ成立 + 全員属性一致(火): 10 * 2.5 * 1.2 = 30.0 x3"""
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.FIRE, power=10.0)
        chars = [make_char(Attribute.FIRE)] * 3
        result = calculate_damage(cards, chars)
        assert result.total_damage == pytest.approx(90.0)

    def test_rainbow_with_partial_bonus(self):
        """レインボー + 火キャラが火カード使用のみボーナス: 10*1.5*1.2 + 10*1.5 + 10*1.5"""
        cards = make_cards(Attribute.FIRE, Attribute.WATER, Attribute.LIGHT, power=10.0)
        chars = [
            make_char(Attribute.FIRE),   # 一致 → 1.2ボーナス
            make_char(Attribute.FIRE),   # 不一致
            make_char(Attribute.FIRE),   # 不一致
        ]
        result = calculate_damage(cards, chars)
        expected = 10 * 1.5 * 1.2 + 10 * 1.5 + 10 * 1.5
        assert result.total_damage == pytest.approx(expected)

    def test_joker_converted_bonus(self):
        """
        [火, 火, 無] → フラッシュ(火)に変換。
        無属性キャラが変換後の火カードを使うため一致ボーナスなし。
        火キャラが変換後の火カードを使うため一致ボーナスあり。
        """
        cards = make_cards(Attribute.FIRE, Attribute.FIRE, Attribute.TYPELESS, power=10.0)
        chars = [
            make_char(Attribute.FIRE),      # index0: 火カード使用 → ボーナス
            make_char(Attribute.FIRE),      # index1: 火カード使用 → ボーナス
            make_char(Attribute.TYPELESS),  # index2: 変換後=火、キャラ=無 → ボーナスなし
        ]
        result = calculate_damage(cards, chars)
        # フラッシュ倍率 2.5: index0,1 → 10*2.5*1.2=30, index2 → 10*2.5=25
        assert result.combo_result.combo_type == ComboType.FLASH
        assert result.card_damages[0] == pytest.approx(30.0)
        assert result.card_damages[1] == pytest.approx(30.0)
        assert result.card_damages[2] == pytest.approx(25.0)
        assert result.total_damage == pytest.approx(85.0)

    def test_typeless_card_no_bonus_when_not_converted(self):
        """TYPELESS カードが変換されず TYPELESS のまま残ることはないが、
        変換後属性とキャラ属性が不一致ならボーナスなし。"""
        cards = make_cards(Attribute.FIRE, Attribute.WATER, Attribute.TYPELESS, power=10.0)
        # [火, 水, 無] → レインボー (無→光)
        chars = [
            make_char(Attribute.LIGHT),  # index0: 変換後=火、キャラ=光 → ボーナスなし
            make_char(Attribute.LIGHT),  # index1: 変換後=水、キャラ=光 → ボーナスなし
            make_char(Attribute.LIGHT),  # index2: 変換後=光、キャラ=光 → ボーナスあり
        ]
        result = calculate_damage(cards, chars)
        assert result.combo_result.combo_type == ComboType.RAINBOW
        assert result.card_damages[0] == pytest.approx(15.0)  # 10*1.5
        assert result.card_damages[1] == pytest.approx(15.0)  # 10*1.5
        assert result.card_damages[2] == pytest.approx(18.0)  # 10*1.5*1.2
        assert result.total_damage == pytest.approx(48.0)

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            calculate_damage(make_cards(Attribute.FIRE, Attribute.FIRE), [make_char(Attribute.FIRE)] * 2)
