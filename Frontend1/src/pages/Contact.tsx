import React from 'react';

const Contact: React.FC = () => {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <h1 className="text-center mb-4">聯絡我們</h1>
          <p className="text-center text-muted mb-5">有任何問題或需要預約服務嗎？請填寫下表，我們會盡快與您聯繫。</p>
          <div className="card bg-surface p-4">
            <form>
              <div className="mb-3">
                <label htmlFor="name" className="form-label">您的姓名</label>
                <input type="text" className="form-control" id="name" required />
              </div>
              <div className="mb-3">
                <label htmlFor="email" className="form-label">電子郵件</label>
                <input type="email" className="form-control" id="email" required />
              </div>
              <div className="mb-3">
                <label htmlFor="subject" className="form-label">主旨</label>
                <input type="text" className="form-control" id="subject" required />
              </div>
              <div className="mb-3">
                <label htmlFor="message" className="form-label">訊息內容</label>
                <textarea className="form-control" id="message" rows={5} required></textarea>
              </div>
              <div className="text-center">
                <button type="submit" className="btn btn-primary btn-lg">送出訊息</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Contact;
