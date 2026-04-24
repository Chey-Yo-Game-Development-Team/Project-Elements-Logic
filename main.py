"""
Project Elements - CLI Game Loop (Phase 4)

models.py / combo_engine.py / hate_system.py を統合した
1バトル完結シミュレーター。

Usage:
  python main.py          # インタラクティブモード（Enterで進行）
  python main.py --auto   # 自動進行モード（テスト用）
"""
from __future__ import annotations

import sys
import io

# Windows 環境での文字化け対策
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from dataclasses import dataclass, field

from models import Attribute, Card, Character, Party, Position
from combo_engine import calculate_damage, ComboType
from hate_system import HateSystem

# ----------------------------------------------------------------
# 表示設定
# ----------------------------------------------------------------
SEP  = "=" * 54
THIN = "-" * 54

ATTR_JP: dict[Attribute, str] = {
    Attribute.FIRE:     "火",
    Attribute.WATER:    "水",
    Attribute.LIGHT:    "光",
    Attribute.TYPELESS: "無",
}
POS_JP: dict[Position, str] = {
    Position.FRONT: "前衛",
    Position.MID:   "中衛",
    Position.BACK:  "後衛",
}
COMBO_JP: dict[ComboType, str] = {
    ComboType.FLASH:   "フラッシュ  (全体 x2.5)",
    ComboType.RAINBOW: "レインボー  (全体 x1.5)",
    ComboType.PAIR:    "ペア        (同色 x1.2 / 他 x1.0)",
    ComboType.NONE:    "役なし      (全体 x1.0)",
}

INTERACTIVE = "--auto" not in sys.argv


# ----------------------------------------------------------------
# 敵クラス（シンプル版）
# ----------------------------------------------------------------
@dataclass
class Enemy:
    name: str
    max_hp: int
    attack_power: int
    current_hp: int = field(init=False)

    def __post_init__(self) -> None:
        self.current_hp = self.max_hp

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0

    def take_damage(self, damage: float) -> None:
        self.current_hp = max(0, self.current_hp - int(damage))


# ----------------------------------------------------------------
# 表示ヘルパー
# ----------------------------------------------------------------
def hp_bar(current: int, max_hp: int, width: int = 20) -> str:
    ratio = max(0.0, current / max_hp)
    filled = int(ratio * width)
    bar = "#" * filled + "." * (width - filled)
    return f"[{bar}] {current:>4}/{max_hp}"


def print_status(party: Party, enemy: Enemy) -> None:
    print(THIN)
    print("  [パーティ]")
    for c in party.characters:
        label = "戦闘不能" if not c.is_alive else POS_JP[c.position]
        print(f"    {c.name:6s} ({label:4s}) {hp_bar(c.current_hp, c.max_hp)}")
    print(f"  [敵] {enemy.name}")
    print(f"         {hp_bar(enemy.current_hp, enemy.max_hp)}")
    print(THIN)


def pause(msg: str = "Enterで続ける...") -> None:
    if INTERACTIVE:
        input(f"  >> {msg}")
    else:
        print(f"  >> {msg}")


# ----------------------------------------------------------------
# ゲームセットアップ
# ----------------------------------------------------------------
def setup() -> tuple[Party, Enemy]:
    """
    パーティ構成:
      アリア  (火 / 前衛): 火カード x3 (威力15)
      リン    (水 / 中衛): 水カード x3 (威力12)
      ルクス  (光 / 後衛): 光カード x2 + 無カード x1 (威力13/10)
    """
    fire_cards  = [Card(Attribute.FIRE,  15.0)] * 3
    water_cards = [Card(Attribute.WATER, 12.0)] * 3
    light_cards = [
        Card(Attribute.LIGHT,    13.0),
        Card(Attribute.LIGHT,    13.0),
        Card(Attribute.TYPELESS, 10.0),
    ]

    characters = [
        Character(
            name="アリア", attribute=Attribute.FIRE,  max_hp=120,
            position=Position.FRONT, cards=fire_cards,  base_hate=10.0,
        ),
        Character(
            name="リン",   attribute=Attribute.WATER, max_hp=100,
            position=Position.MID,   cards=water_cards, base_hate=10.0,
        ),
        Character(
            name="ルクス", attribute=Attribute.LIGHT, max_hp=80,
            position=Position.BACK,  cards=light_cards, base_hate=10.0,
        ),
    ]

    party = Party(characters, leader_attribute=Attribute.FIRE)
    enemy = Enemy(name="ダークドラゴン", max_hp=300, attack_power=25)
    return party, enemy


# ----------------------------------------------------------------
# 1ターンの処理
# ----------------------------------------------------------------
def process_turn(turn: int, party: Party, enemy: Enemy) -> str | None:
    """
    1ターンを処理する。
    Returns: "win" | "lose" | None（バトル継続）
    """
    print()
    print(SEP)
    print(f"  ■ ターン {turn}")
    print(SEP)

    # ── 1. 手札表示 ──────────────────────────────────────
    hand = party.hand  # play_hand() を呼ぶ前に参照を保持
    print("\n  [手札]")
    for i, (card, char) in enumerate(zip(hand, party.characters)):
        print(
            f"    スロット{i + 1}: [{ATTR_JP[card.attribute]}]  "
            f"威力 {card.base_power:>4.0f}  "
            f"(使用者: {char.name} / {POS_JP[char.position]})"
        )

    print()
    pause("3枚すべてプレイ！ ")

    # ── 2. コンボ判定・ダメージ計算 ──────────────────────
    casters = list(party.characters)
    result  = calculate_damage(hand, casters, leader_attribute=party.leader_attribute)
    combo   = result.combo_result

    print(f"\n  [コンボ判定]")
    print(f"    変換後属性: {' / '.join(ATTR_JP[a] for a in combo.resolved_attributes)}")
    print(f"    成立役    : {COMBO_JP[combo.combo_type]}")

    print(f"\n  [ダメージ内訳]")
    for i, (card, char, dmg) in enumerate(zip(hand, casters, result.card_damages)):
        resolved = combo.resolved_attributes[i]
        bonus = " ★属性一致 (+20%)" if (
            resolved == char.attribute and resolved != Attribute.TYPELESS
        ) else ""
        print(
            f"    {char.name}: [{ATTR_JP[resolved]}] → "
            f"{dmg:>7.1f} ダメージ{bonus}"
        )

    total = result.total_damage
    print(f"\n    合計ダメージ: {total:.1f}")
    enemy.take_damage(total)

    # ── 3. ヘイト蓄積 ────────────────────────────────────
    for char in party.characters:
        if char.is_alive:
            HateSystem.add_hate(char, 5.0)

    # ── 4. 手札を消費 → 次の手札を補充（3周目でリシャッフル） ──
    party.play_hand()
    if turn % 3 == 0:
        print(f"\n  ★ デッキが1周しました！ カードをリシャッフルします。")

    # ── 5. 勝利判定 ──────────────────────────────────────
    if not enemy.is_alive:
        return "win"

    # ── 6. 敵の反撃 ──────────────────────────────────────
    print(f"\n  [{enemy.name}の反撃]")
    alive  = party.alive_characters
    target = HateSystem.select_target(party.characters)

    if target is None:
        print("    ターゲットなし（全員戦闘不能）")
    else:
        eff_hate = HateSystem.get_effective_hate(target, alive)
        print(
            f"    ターゲット: {target.name}（{POS_JP[target.position]}）"
            f"  実効ヘイト={eff_hate:.1f}"
        )
        target.take_damage(enemy.attack_power)
        print(
            f"    {target.name} が {enemy.attack_power} ダメージ！  "
            f"HP: {target.current_hp}/{target.max_hp}"
        )

    # ── 7. 敗北判定 ──────────────────────────────────────
    if not party.alive_characters:
        return "lose"

    return None  # バトル継続


# ----------------------------------------------------------------
# エントリポイント
# ----------------------------------------------------------------
def main() -> None:
    print()
    print(SEP)
    print("          プロジェクト・エレメンツ")
    print("              バトル開始！")
    print(SEP)

    party, enemy = setup()
    print_status(party, enemy)
    print()
    pause("ゲームスタート！")

    turn    = 0
    outcome = None

    while outcome is None:
        turn   += 1
        outcome = process_turn(turn, party, enemy)

        if outcome is None:
            print()
            print_status(party, enemy)
            print()
            pause("次のターンへ... ")

    # 最終状態・結果表示
    print()
    print_status(party, enemy)
    print(SEP)
    if outcome == "win":
        print(f"  勝利！ {enemy.name} を {turn} ターンで撃破！")
    else:
        print(f"  敗北... パーティが全滅しました。({turn} ターン経過)")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
