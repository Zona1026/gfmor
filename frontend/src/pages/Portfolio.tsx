import React, { useState, useEffect } from 'react';

// Define the portfolio item type based on schemas.py
interface PortfolioItem {
  id: number;
  title: string;
  description: string | null;
  category: string;
  image_url: string;
  created_at: string; // Assuming datetime is serialized as a string
}

const Portfolio: React.FC = () => {
  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPortfolioItems = async () => {
      // Determine API base URL based on environment
      const apiBaseUrl = process.env.NODE_ENV === 'production' 
        ? 'https://gfmor.onrender.com' 
        : 'http://localhost:8000';
      
      try {
        setLoading(true);
        const response = await fetch(`${apiBaseUrl}/api/portfolios`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: PortfolioItem[] = await response.json();
        setItems(data);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolioItems();
  }, []); // Empty dependency array ensures this runs once on mount

  const apiBaseUrl = process.env.NODE_ENV === 'production' 
    ? 'https://gfmor.onrender.com' 
    : 'http://localhost:8000';

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4">作品集</h1>
      <p className="text-center text-muted mb-5">見證我們的工藝與熱情</p>

      {loading && <p className="text-center">載入中...</p>}
      {error && <p className="text-center text-danger">讀取作品失敗: {error}</p>}
      
      {!loading && !error && (
        <div className="row g-4">
          {items.map((item) => (
            <div className="col-md-6 col-lg-4" key={item.id}>
              <div className="card bg-surface text-white h-100">
                <div
                  style={{
                    height: '250px',
                    background: `url('${apiBaseUrl}${item.image_url}') no-repeat center center/cover`,
                  }}
                  aria-label={item.title}
                ></div>
                <div className="card-body d-flex flex-column">
                  <h5 className="card-title">{item.title}</h5>
                  <p className="card-text flex-grow-1">{item.description || '暫無描述'}</p>
                  <small className="text-muted">{item.category}</small>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Portfolio;
