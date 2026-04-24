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


def make_char(attr: Attribute = Attribute.FIRE, position: Position = Position.MID, name: str = "test") -> Character:
    """テスト用キャラクターを生成する（カードは3枚のダミーで固定）。"""
    cards = [Card(attr, 10.0)] * 3
    return Character(name=name, max_hp=100, position=position, cards=cards)


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
    """装備者一致ボーナス（1.2x）の動作を検証する。"""

    def _chars(self, attrs):
        """個別名付きキャラクターを生成する。各キャラのカードはそれぞれのキャラがオーナー。"""
        names = ["alice", "bob", "carol"]
        return [
            Character(name=n, max_hp=100, position=Position.MID,
                      cards=[Card(a, 10.0)] * 3)
            for n, a in zip(names, attrs)
        ]

    def test_flash_no_bonus_other_chars_cards(self):
        """フラッシュ + 全員が他キャラのカードを使用: 10 * 2.5 = 25.0 x3"""
        chars = self._chars([Attribute.FIRE] * 3)
        # 循環swap: alice→bob's, bob→carol's, carol→alice's
        hand = [chars[1].cards[0], chars[2].cards[0], chars[0].cards[0]]
        result = calculate_damage(hand, chars)
        assert result.total_damage == pytest.approx(75.0)

    def test_flash_with_bonus_own_cards(self):
        """フラッシュ + 全員が自分のカードを使用: 10 * 2.5 * 1.2 = 30.0 x3"""
        chars = self._chars([Attribute.FIRE] * 3)
        hand = [chars[0].cards[0], chars[1].cards[0], chars[2].cards[0]]
        result = calculate_damage(hand, chars)
        assert result.total_damage == pytest.approx(90.0)

    def test_rainbow_all_own_cards_bonus(self):
        """レインボー + 全員が自分のカードを使用: 10 * 1.5 * 1.2 = 18.0 x3"""
        chars = self._chars([Attribute.FIRE, Attribute.WATER, Attribute.LIGHT])
        hand = [chars[0].cards[0], chars[1].cards[0], chars[2].cards[0]]
        result = calculate_damage(hand, chars)
        assert result.combo_result.combo_type == ComboType.RAINBOW
        assert result.total_damage == pytest.approx(54.0)

    def test_rainbow_partial_own_cards(self):
        """レインボー + 1人のみ自分のカード: そのキャラだけボーナス"""
        chars = self._chars([Attribute.FIRE, Attribute.WATER, Attribute.LIGHT])
        # alice: own(fire), bob: carol's(light), carol: bob's(water)
        hand = [chars[0].cards[0], chars[2].cards[0], chars[1].cards[0]]
        result = calculate_damage(hand, chars)
        assert result.combo_result.combo_type == ComboType.RAINBOW
        assert result.card_damages[0] == pytest.approx(18.0)  # 10*1.5*1.2 (own)
        assert result.card_damages[1] == pytest.approx(15.0)  # 10*1.5
        assert result.card_damages[2] == pytest.approx(15.0)  # 10*1.5
        assert result.total_damage == pytest.approx(48.0)

    def test_joker_own_card_gets_bonus(self):
        """
        [火, 火, 無] → フラッシュ(火)に変換。
        無属性カードも自分のカードなら変換後にボーナス適用。
        """
        chars = self._chars([Attribute.FIRE, Attribute.FIRE, Attribute.TYPELESS])
        hand = [chars[0].cards[0], chars[1].cards[0], chars[2].cards[0]]
        result = calculate_damage(hand, chars)
        assert result.combo_result.combo_type == ComboType.FLASH
        assert result.card_damages[0] == pytest.approx(30.0)  # 10*2.5*1.2
        assert result.card_damages[1] == pytest.approx(30.0)  # 10*2.5*1.2
        assert result.card_damages[2] == pytest.approx(30.0)  # 10*2.5*1.2 (自分の無属性カード)
        assert result.total_damage == pytest.approx(90.0)

    def test_joker_other_chars_card_no_bonus(self):
        """他キャラの無属性カードを使用した場合はボーナスなし。"""
        chars = self._chars([Attribute.FIRE, Attribute.FIRE, Attribute.TYPELESS])
        # carol(無)のカードを alice がプレイ、alice のカードを carol がプレイ
        hand = [chars[2].cards[0], chars[1].cards[0], chars[0].cards[0]]
        result = calculate_damage(hand, chars)
        assert result.combo_result.combo_type == ComboType.FLASH
        assert result.card_damages[0] == pytest.approx(25.0)  # 10*2.5 (他キャラのカード)
        assert result.card_damages[1] == pytest.approx(30.0)  # 10*2.5*1.2 (own)
        assert result.card_damages[2] == pytest.approx(25.0)  # 10*2.5 (他キャラのカード)
        assert result.total_damage == pytest.approx(80.0)

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            calculate_damage(make_cards(Attribute.FIRE, Attribute.FIRE), [make_char()] * 2)


# ---------------------------------------------------------------------------
# §2-4 新仕様: 装備者一致ボーナス
# ---------------------------------------------------------------------------

class TestOwnershipBonus:
    """「自分がセットしたカードを使うとボーナス」の新ロジックを検証する。"""

    def _make_named_char(self, name: str, attr: Attribute, position: Position = Position.MID) -> Character:
        cards = [Card(attr, 10.0)] * 3
        return Character(name=name, max_hp=100, position=position, cards=cards)

    def test_flash_all_own_cards_bonus(self):
        """フラッシュ + 全員が自分のカードを使用: 10 * 2.5 * 1.2 = 30.0 x3"""
        char_a = self._make_named_char("alice", Attribute.FIRE)
        char_b = self._make_named_char("bob",   Attribute.FIRE)
        char_c = self._make_named_char("carol", Attribute.FIRE)
        hand = [char_a.cards[0], char_b.cards[0], char_c.cards[0]]
        result = calculate_damage(hand, [char_a, char_b, char_c])
        assert result.combo_result.combo_type == ComboType.FLASH
        assert result.total_damage == pytest.approx(90.0)

    def test_flash_no_own_cards_no_bonus(self):
        """フラッシュ + 全員が他キャラのカードを使用: 10 * 2.5 = 25.0 x3"""
        char_a = self._make_named_char("alice", Attribute.FIRE)
        char_b = self._make_named_char("bob",   Attribute.FIRE)
        char_c = self._make_named_char("carol", Attribute.FIRE)
        # 循環swap: alice→bob's, bob→carol's, carol→alice's
        hand = [char_b.cards[0], char_c.cards[0], char_a.cards[0]]
        result = calculate_damage(hand, [char_a, char_b, char_c])
        assert result.combo_result.combo_type == ComboType.FLASH
        assert result.total_damage == pytest.approx(75.0)

    def test_partial_own_card_bonus(self):
        """フラッシュ + 1人だけ自分のカードを使用: そのキャラのみボーナス"""
        char_a = self._make_named_char("alice", Attribute.FIRE)
        char_b = self._make_named_char("bob",   Attribute.FIRE)
        char_c = self._make_named_char("carol", Attribute.FIRE)
        # alice: 自分, bob: carol's, carol: bob's
        hand = [char_a.cards[0], char_c.cards[0], char_b.cards[0]]
        result = calculate_damage(hand, [char_a, char_b, char_c])
        assert result.card_damages[0] == pytest.approx(30.0)  # 10*2.5*1.2 (own)
        assert result.card_damages[1] == pytest.approx(25.0)  # 10*2.5 (other)
        assert result.card_damages[2] == pytest.approx(25.0)  # 10*2.5 (other)
        assert result.total_damage == pytest.approx(80.0)

    def test_typeless_own_card_gets_bonus(self):
        """無属性カードも自分のカードなら変換後にボーナス適用。"""
        char_a = self._make_named_char("alice", Attribute.FIRE)
        char_b = self._make_named_char("bob",   Attribute.FIRE)
        char_c = self._make_named_char("carol", Attribute.TYPELESS)
        hand = [char_a.cards[0], char_b.cards[0], char_c.cards[0]]
        result = calculate_damage(hand, [char_a, char_b, char_c])
        assert result.combo_result.combo_type == ComboType.FLASH
        # carol も自分のカード(無→火変換)なのでボーナスあり
        assert result.card_damages[2] == pytest.approx(30.0)
        assert result.total_damage == pytest.approx(90.0)
