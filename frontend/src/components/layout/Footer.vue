<template>
  <footer class="site-footer">
    <div class="footer-container">
      <div class="footer-info">
        <h3>GFmotor 廣發汽修</h3>
        <p>專業二輪維修、保養與精品改裝。提供最值得信賴的技術與服務。</p>
        <div class="social-links">
          <!-- 預留社交媒體連結 -->
        </div>
      </div>
      
      <div class="footer-nav">
        <h4>快速連結</h4>
        <ul>
          <li><router-link to="/">首頁</router-link></li>
          <li><router-link to="/booking">預約維修</router-link></li>
          <li><router-link to="/products">精品商城</router-link></li>
        </ul>
      </div>

      <div class="footer-legal">
        <h4>法律條款</h4>
        <ul>
          <li><router-link to="/privacy">隱私權政策</router-link></li>
          <li><router-link to="/terms">服務條款與免責聲明</router-link></li>
        </ul>
      </div>

      <div class="footer-contact">
        <h4>聯繫我們</h4>
        <p>📍 高雄市某某區某某路123號</p>
        <p>📞 07-1234567</p>
        <p>⏰ 週一至週六 13:00 - 22:00</p>
      </div>
    </div>
    
    <div class="footer-bottom">
      <p>&copy; 2024 GFmotor 廣發汽修. All rights reserved.</p>
    </div>
  </footer>
</template>

<style lang="scss" scoped>
@import '../../assets/_variables.scss';

.site-footer {
  background-color: darken($background-color, 3%);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding: 4rem 1rem 1rem;
  margin-top: 4rem;
  color: $text-secondary;

  .footer-container {
    max-width: 1200px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1.5fr;
    gap: 3rem;
  }

  h3 {
    color: $primary-color;
    margin-bottom: 1.5rem;
    font-size: 1.5rem;
  }

  h4 {
    color: $text-primary;
    margin-bottom: 1.5rem;
    font-size: 1.1rem;
    font-weight: 600;
  }

  p {
    line-height: 1.6;
    margin-bottom: 1rem;
    font-size: 0.95rem;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;

    li {
      margin-bottom: 0.8rem;
      
      a {
        color: $text-secondary;
        text-decoration: none;
        transition: color 0.3s;
        font-size: 0.95rem;
        
        &:hover {
          color: $primary-color;
        }
      }
    }
  }

  .footer-bottom {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    text-align: center;
    
    p {
      font-size: 0.85rem;
      color: $text-disabled;
    }
  }

  @media (max-width: 992px) {
    .footer-container {
      grid-template-columns: 1fr 1fr;
    }
  }

  @media (max-width: 576px) {
    padding-top: 3rem;
    .footer-container {
      grid-template-columns: 1fr;
      gap: 2rem;
    }
    
    .footer-bottom {
      margin-top: 2rem;
    }
  }
}
</style>
