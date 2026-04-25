// Ver-C#/Scripts/Data/CardData.cs
// カードのマスターデータ。ScriptableObject としてエディタ上で作成・編集できる。

using UnityEngine;
using ProjectElements.Core;

namespace ProjectElements.Data
{
    /// <summary>
    /// カード1枚のマスターデータ。
    /// UnityエディタのProject窓から「Create > ProjectElements > CardData」で作成する。
    /// </summary>
    [CreateAssetMenu(
        fileName  = "New CardData",
        menuName  = "ProjectElements/CardData",
        order     = 1)]
    public class CardData : ScriptableObject
    {
        [Header("基本情報")]

        [Tooltip("カードの表示名（例: 炎の斬撃）")]
        public string cardName = "New Card";

        [Tooltip("カードの属性。Typeless はジョーカーとして機能する。")]
        public Element element = Element.Fire;

        [Tooltip("このカードの基礎威力。ダメージ計算の乗算元になる。")]
        [Min(0f)]
        public float basePower = 10f;

        // -----------------------------------------------------------------
        // 所有者 (owner) は実行時に CharacterData または BattleCharacter が
        // 設定するため、マスターデータには持たせない。
        // -----------------------------------------------------------------
    }
}
