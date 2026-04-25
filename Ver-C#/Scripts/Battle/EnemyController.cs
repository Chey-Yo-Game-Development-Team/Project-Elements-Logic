// Ver-C#/Scripts/Battle/EnemyController.cs
// Python の Enemy dataclass（main.py）を Unity の MonoBehaviour として移植。
// インスペクターから名前・HP・攻撃力を設定できる。

using System.Collections;
using UnityEngine;

namespace ProjectElements.Battle
{
    /// <summary>
    /// 敵キャラクターの状態と行動を管理する MonoBehaviour。
    /// BattleManager から参照される。
    /// </summary>
    public class EnemyController : MonoBehaviour
    {
        // -----------------------------------------------------------------
        // インスペクター設定（静的パラメータ）
        // -----------------------------------------------------------------

        [Header("基本情報")]

        [Tooltip("敵の表示名（例: ダークドラゴン）")]
        [SerializeField] private string enemyName = "ダークドラゴン";

        [Tooltip("最大HP。バトル開始時の CurrentHp 初期値になる。")]
        [SerializeField, Min(1)] private int maxHp = 300;

        [Tooltip("1回の攻撃で与えるダメージ量（固定値）。")]
        [SerializeField, Min(0)] private int attackPower = 25;

        // -----------------------------------------------------------------
        // ランタイム状態
        // -----------------------------------------------------------------

        private MeshRenderer _meshRenderer;
        private Material     _instanceMaterial;
        private Color        _originalColor;
        private bool _isDying;

        /// <summary>現在HP。0 以下で戦闘不能。</summary>
        public int CurrentHp { get; private set; }

        // -----------------------------------------------------------------
        // 算出プロパティ
        // -----------------------------------------------------------------

        public string EnemyName   => enemyName;
        public int    MaxHp       => maxHp;
        public int    AttackPower => attackPower;

        /// <summary>生存判定。</summary>
        public bool IsAlive => CurrentHp > 0;

        /// <summary>HP割合（0.0 〜 1.0）。UI表示用。</summary>
        public float HpRatio => (float)CurrentHp / maxHp;

        // -----------------------------------------------------------------
        // Unity ライフサイクル
        // -----------------------------------------------------------------

        private void Awake()
        {
            CurrentHp = maxHp;
            _meshRenderer = GetComponent<MeshRenderer>();
            if (_meshRenderer != null)
            {
                _instanceMaterial = _meshRenderer.material;
                _originalColor    = _instanceMaterial.color;
            }
        }

        // -----------------------------------------------------------------
        // バトル操作
        // -----------------------------------------------------------------

        /// <summary>
        /// バトル開始時に HP をリセットする。BattleManager.StartBattle() から呼ぶ。
        /// </summary>
        public void Initialize()
        {
            StopAllCoroutines();
            CurrentHp = maxHp;
            _isDying  = false;
            gameObject.SetActive(true);
            if (_instanceMaterial != null)
                _instanceMaterial.color = _originalColor;
        }

        /// <summary>
        /// ダメージを受ける。CurrentHp は 0 未満にはならない。
        /// Python の Enemy.take_damage() に相当。
        /// </summary>
        /// <param name="damage">受けるダメージ量（小数点以下は切り捨て）</param>
        public void TakeDamage(float damage)
        {
            if (_isDying) return;

            CurrentHp = Mathf.Max(0, CurrentHp - Mathf.FloorToInt(damage));
            if (CurrentHp <= 0)
            {
                _isDying = true;
                StopAllCoroutines();
                StartCoroutine(DieRoutine());
            }
            else
            {
                StartCoroutine(HitFlashRoutine());
            }
        }

        private IEnumerator HitFlashRoutine()
        {
            if (_meshRenderer == null) yield break;
            _instanceMaterial.color = Color.red;
            yield return new WaitForSeconds(0.2f);
            _instanceMaterial.color = _originalColor;
        }

        private IEnumerator DieRoutine()
        {
            if (_instanceMaterial != null)
                _instanceMaterial.color = Color.gray;
            yield return new WaitForSeconds(1f);
            gameObject.SetActive(false);
        }

        public override string ToString()
        {
            return $"{enemyName} (HP:{CurrentHp}/{maxHp})";
        }
    }
}
