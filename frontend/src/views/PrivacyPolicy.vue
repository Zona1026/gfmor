<template>
  <div class="legal-page">
    <div class="container">
      <h1>隱私權政策 (Privacy Policy)</h1>
      <p class="last-updated">最後更新日期：2024年5月</p>

      <section>
        <h2>1. 個人資料的收集</h2>
        <p>當您使用 GFmotor 的服務（包括但不限於透過 Google 帳號登入、進行預約、購買商品）時，我們可能會收集您的以下個人資料：</p>
        <ul>
          <li>基本資料：姓名、電子郵件地址。</li>
          <li>聯繫方式：電話號碼。</li>
          <li>車輛資訊：品牌、型號、車牌號碼、引擎號碼、里程數。</li>
          <li>交易紀錄：購買商品或預約服務的相關紀錄。</li>
        </ul>
      </section>

      <section>
        <h2>2. 個人資料的使用目的</h2>
        <p>收集您的個人資料主要是為了：</p>
        <ul>
          <li>提供與維護服務：如處理您的預約請求、訂單配送。</li>
          <li>身分驗證：透過 Google OAuth 確保帳號安全。</li>
          <li>售後服務：管理您的車輛維修紀錄。</li>
          <li>通知與聯繫：發送服務通知、促銷活動（如您已同意）。</li>
        </ul>
      </section>

      <section>
        <h2>3. 資料保護與安全</h2>
        <p>我們致力於保護您的個人資料安全。我們使用業界標準的加密技術（如 SSL/TLS）來保護資料傳輸過程中的安全，並將資料儲存在受保護的伺服器中。</p>
      </section>

      <section>
        <h2>4. 第三方連結與服務</h2>
        <p>我們的網站可能包含第三方網站的連結（例如 Google 登入）。這些第三方網站有其獨立的隱私權政策，我們對其內容與行為不負法律責任。</p>
      </section>

      <section>
        <h2>5. Cookie 的使用</h2>
        <p>我們使用 Cookie 來提升您的瀏覽體驗、記住您的登入狀態以及分析網站流量。您可以在瀏覽器設定中選擇拒絕 Cookie，但這可能會導致網站部分功能無法正常運作。</p>
      </section>

      <section>
        <h2>6. 隱私權政策的變更</h2>
        <p>GFmotor 保留隨時修改本隱私權政策的權利。任何變更都將公告於此頁面。建議您定期查看以瞭解最新資訊。</p>
      </section>

      <section>
        <h2>7. 聯繫我們</h2>
        <p>如果您對本隱私權政策有任何疑問，歡迎聯繫我們：<br>
        Email: gfmotor.service@gmail.com</p>
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
