import React from 'react';

const Portfolio: React.FC = () => {
  // Placeholder data for portfolio items
  const portfolioItems = new Array(6).fill(0);

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4">作品集</h1>
      <p className="text-center text-muted mb-5">見證我們的工藝與熱情</p>
      <div className="row g-4">
        {portfolioItems.map((_, index) => (
          <div className="col-md-6 col-lg-4" key={index}>
            <div className="card bg-surface text-white">
              <div
                style={{
                  height: '250px',
                  background: `url('https://via.placeholder.com/400x300/000000/FFFFFF?text=Project+${index + 1}') no-repeat center center/cover`,
                }}
              ></div>
              <div className="card-body">
                <h5 className="card-title">改裝專案 #{index + 1}</h5>
                <p className="card-text">這是一段關於此改裝專案的簡短描述，突顯其特色與使用的技術。</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Portfolio;
