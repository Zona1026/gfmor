import React from 'react';

const Services: React.FC = () => {
  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4">服務項目</h1>
      <div className="row">
        {/* 維修 */}
        <div className="col-md-4 mb-4">
          <div className="card bg-surface text-white h-100">
            <div className="card-body">
              <h3 className="card-title text-primary">維修</h3>
              <p className="card-text">從引擎問題到電路故障，我們擁有最專業的技術與工具，快速診斷並解決您愛車的一切問題。</p>
            </div>
          </div>
        </div>
        {/* 保養 */}
        <div className="col-md-4 mb-4">
          <div className="card bg-surface text-white h-100">
            <div className="card-body">
              <h3 className="card-title text-primary">保養</h3>
              <p className="card-text">提供全方位的定期保養服務，包括更換機油、輪胎檢查、煞車系統維護等，確保您的行車安全。</p>
            </div>
          </div>
        </div>
        {/* 改裝 */}
        <div className="col-md-4 mb-4">
          <div className="card bg-surface text-white h-100">
            <div className="card-body">
              <h3 className="card-title text-primary">改裝</h3>
              <p className="card-text">無論是性能提升還是外觀客製化，我們的專家團隊都能協助您打造出獨一無二的夢想座駕。</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Services;
