// Ver-C#/Scripts/Models/BattleCharacter.cs
// バトル中に生成される動的な状態を管理するクラス。
// MonoBehaviour は継承せず、純粋な C# クラスとして設計。
// 静的データは CharacterData (ScriptableObject) を参照する。

using System;
using ProjectElements.Core;
using ProjectElements.Data;

namespace ProjectElements.Models
{
    /// <summary>
    /// バトル開始時に CharacterData から生成されるランタイムオブジェクト。
    /// 現在HP・ヘイト値・ポジションなどの「バトル中に変化する状態」を保持する。
    /// </summary>
    public class BattleCharacter
    {
        // -----------------------------------------------------------------
        // 静的データへの参照（読み取り専用）
        // -----------------------------------------------------------------

        /// <summary>変更されない元のマスターデータ。</summary>
        public CharacterData Data { get; }

        // -----------------------------------------------------------------
        // 動的状態（バトル中に変化する値）
        // -----------------------------------------------------------------

        /// <summary>現在HP。0 以下になると戦闘不能。</summary>
        public int CurrentHp { get; private set; }

        /// <summary>
        /// 基礎ヘイト値。行動するたびに HateSystem.AddHate() で加算される。
        /// 実効ヘイトスコアの計算式: 基礎ヘイト × ポジション倍率
        /// </summary>
        public float BaseHate { get; set; }

        /// <summary>
        /// 現在の配置ポジション。バトル開始時に Party が設定する。
        /// ポジションは基本的に固定だが、エッジケース処理で HateSystem が
        /// 動的倍率を上書きするため、ここでは配置情報のみを保持する。
        /// </summary>
        public Position Position { get; set; }

        // -----------------------------------------------------------------
        // 算出プロパティ
        // -----------------------------------------------------------------

        /// <summary>生存判定。</summary>
        public bool IsAlive => CurrentHp > 0;

        /// <summary>HP割合（0.0 〜 1.0）。ターゲット選定の同値タイブレークに使用する。</summary>
        public float HpRatio => (float)CurrentHp / Data.maxHp;

        /// <summary>
        /// 固定ポジション倍率を使った実効ヘイトスコア。
        /// 後衛全滅時の動的繰り上げが必要な場合は HateSystem.GetEffectiveHate() を使うこと。
        /// </summary>
        public float EffectiveHate => BaseHate * Position.GetBaseHateMultiplier();

        // 便利アクセサ（CharacterData の値をショートカット）
        public string  Name         => Data.characterName;
        public int     MaxHp        => Data.maxHp;
        public float   AttackPower  => Data.attackPower;
        public Element Element  => Data.element;
        public CardData[] Cards     => Data.cards;

        // -----------------------------------------------------------------
        // コンストラクタ
        // -----------------------------------------------------------------

        /// <summary>
        /// CharacterData とポジションを指定してバトルキャラクターを生成する。
        /// </summary>
        /// <param name="data">ScriptableObject のマスターデータ</param>
        /// <param name="position">バトル開始時のポジション</param>
        public BattleCharacter(CharacterData data, Position position)
        {
            Data      = data ?? throw new ArgumentNullException(nameof(data));
            Position  = position;
            CurrentHp = data.maxHp;
            BaseHate  = data.initialBaseHate;
        }

        // -----------------------------------------------------------------
        // バトル中の操作メソッド
        // -----------------------------------------------------------------

        /// <summary>
        /// ダメージを受ける。CurrentHp は 0 未満にはならない。
        /// </summary>
        /// <param name="damage">受けるダメージ量（小数点以下は切り捨て）</param>
        public void TakeDamage(float damage)
        {
            int dmgInt = (int)damage;
            CurrentHp  = Math.Max(0, CurrentHp - dmgInt);
        }

        /// <summary>
        /// HPを回復する。MaxHp を超えない。
        /// </summary>
        /// <param name="amount">回復量</param>
        public void Heal(int amount)
        {
            CurrentHp = Math.Min(MaxHp, CurrentHp + amount);
        }

        public override string ToString()
        {
            return $"BattleCharacter({Name}, HP:{CurrentHp}/{MaxHp}, {Position})";
        }
    }
}
