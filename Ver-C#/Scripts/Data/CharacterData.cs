// Ver-C#/Scripts/Data/CharacterData.cs
// キャラクターのマスターデータ（静的な固定値）。
// バトル中の動的状態（現在HP、ヘイト値など）は BattleCharacter が管理する。

using UnityEngine;
using ProjectElements.Core;

namespace ProjectElements.Data
{
    /// <summary>
    /// キャラクター1人の静的マスターデータ。
    /// UnityエディタのProject窓から「Create > ProjectElements > CharacterData」で作成する。
    /// </summary>
    [CreateAssetMenu(
        fileName  = "New CharacterData",
        menuName  = "ProjectElements/CharacterData",
        order     = 2)]
    public class CharacterData : ScriptableObject
    {
        [Header("基本情報")]

        [Tooltip("キャラクターの表示名（例: アリア）")]
        public string characterName = "New Character";

        [Tooltip("キャラクターの属性。")]
        public Attribute attribute = Attribute.Fire;

        // -----------------------------------------------------------------
        // 静的パラメータ（エディタで設定する固定値）
        // -----------------------------------------------------------------
        [Header("バトルパラメータ")]

        [Tooltip("最大HP。バトル開始時に BattleCharacter.CurrentHp の初期値になる。")]
        [Min(1)]
        public int maxHp = 100;

        [Tooltip("基礎攻撃力。コンボ倍率・ボーナス倍率の乗算元になる。")]
        [Min(0f)]
        public float attackPower = 10f;

        [Tooltip("バトル開始時の初期基礎ヘイト値。行動のたびに HateSystem が加算する。")]
        [Min(0f)]
        public float initialBaseHate = 10f;

        // -----------------------------------------------------------------
        // カードデータ（3枚固定）
        // -----------------------------------------------------------------
        [Header("所持カード（必ず3枚設定すること）")]

        [Tooltip("このキャラクターが所持する固有カード。要素数は必ず3にすること。")]
        public CardData[] cards = new CardData[3];

        // -----------------------------------------------------------------
        // エディタ上の簡易バリデーション
        // -----------------------------------------------------------------
        private void OnValidate()
        {
            if (cards == null || cards.Length != 3)
            {
                Debug.LogWarning(
                    $"[CharacterData] {characterName} のカードは3枚必要です（現在: {cards?.Length ?? 0}枚）",
                    this);
            }
        }
    }
}
