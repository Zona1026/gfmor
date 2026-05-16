<template>
  <div class="legal-page">
    <div class="container">
      <h1>服務條款與免責聲明</h1>
      <p class="last-updated">最後更新日期：2024年5月</p>

      <section>
        <h2>1. 服務描述</h2>
        <p>GFmotor 提供機車維修預約、保養紀錄管理、零件商城等相關服務。我們保留隨時更新、暫停或停止服務內容的權利，恕不另行通知。</p>
      </section>

      <section>
        <h2>2. 使用者帳號安全</h2>
        <p>您同意在使用 Google OAuth 登入時提供真實、正確且完整的資訊。您必須對您帳號下發生的所有活動負全部責任。若發現帳號遭到未經授權使用，應立即通知我們。</p>
      </section>

      <section>
        <h2>3. 預約服務規則</h2>
        <ul>
          <li>預約僅表示您選擇了一個偏好的時段，最終仍以店家確認為準。</li>
          <li>若需修改或取消預約，請至少提前 2 小時透過系統或電話聯繫。</li>
          <li>若無故遲到超過 15 分鐘，店家有權取消該次預約。</li>
        </ul>
      </section>

      <section>
        <h2>4. 免責聲明 (Disclaimer)</h2>
        <ul>
          <li><strong>資訊準確性：</strong>本網站所提供的商品資訊、維修建議僅供參考。我們致力於確保資訊準確，但對於任何遺漏或錯誤不承擔任何法律責任。</li>
          <li><strong>維修風險：</strong>機車維修涉及機械作業，所有維修項目的保固期與責任歸屬以實體店面簽署之單據為準。</li>
          <li><strong>系統可用性：</strong>我們不保證網站服務不會中斷、及時、安全或無錯誤。對於因網路問題、駭客攻擊或不可抗力因素導致的資料損失，我們不負賠償責任。</li>
        </ul>
      </section>

      <section>
        <h2>5. 知識產權</h2>
        <p>本網站上所有的內容（文字、圖像、Logo、排版設計）均屬 GFmotor 所有或已獲得合法授權使用。未經書面許可，禁止任何形式的轉載或再利用。</p>
      </section>

      <section>
        <h2>6. 爭議解決</h2>
        <p>本條款之解釋與適用，悉依中華民國法律為準。因本服務所生之爭議，雙方同意以台灣高雄地方法院為第一審管轄法院。</p>
      </section>
      
      <div class="back-home">
        <router-link to="/" class="btn-primary">回到首頁</router-link>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '../assets/_variables.scss';

.legal-page {
  padding: 4rem 1rem;
  background-color: $background-color;
  color: $text-primary;
  min-height: 80vh;

  .container {
    max-width: 800px;
    margin: 0 auto;
  }

  h1 {
    color: $primary-color;
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
  }

  .last-updated {
    color: $text-disabled;
    font-size: 0.9rem;
    margin-bottom: 3rem;
  }

  section {
    margin-bottom: 2.5rem;

    h2 {
      color: $primary-light;
      font-size: 1.5rem;
      margin-bottom: 1rem;
      border-left: 4px solid $primary-color;
      padding-left: 1rem;
    }

    p, li {
      color: $text-secondary;
      line-height: 1.8;
      margin-bottom: 0.8rem;
    }

    ul {
      padding-left: 1.5rem;
    }
    
    strong {
      color: $primary-light;
    }
  }

  .back-home {
    margin-top: 4rem;
    text-align: center;
    
    .btn-primary {
      padding: 0.8rem 2rem;
      background-color: $primary-color;
      color: #fff;
      text-decoration: none;
      border-radius: $border-radius;
      font-weight: bold;
      transition: background 0.3s;
      &:hover { background-color: $primary-dark; }
    }
  }

  @media (max-width: 768px) {
    padding: 2rem 1rem;
    h1 { font-size: 1.8rem; }
    section h2 { font-size: 1.3rem; }
  }
}
</style>
