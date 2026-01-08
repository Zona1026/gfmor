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
  const [error, setError] = useState<any>(null); // Changed to 'any' to capture more error details

  // Determine API base URL based on Vite's environment variable
  const apiBaseUrl = import.meta.env.MODE === 'production' 
    ? 'https://gfmor.onrender.com' 
    : 'http://localhost:8000';

  useEffect(() => {
    const fetchPortfolioItems = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await fetch(`${apiBaseUrl}/api/portfolios`);
        if (!response.ok) {
          // Try to get more error details from the response body
          const errorBody = await response.text();
          throw new Error(`HTTP error! status: ${response.status}, body: ${errorBody}`);
        }
        const data: PortfolioItem[] = await response.json();
        setItems(data);
      } catch (e: any) {
        setError(e);
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolioItems();
  }, [apiBaseUrl]); // Added apiBaseUrl as a dependency

  return (
    <div className="container mt-5">
      <h1 className="text-center mb-4">作品集</h1>
      <p className="text-center text-muted mb-5">見證我們的工藝與熱情</p>

      {/* --- DEBUGGING INFO (TEMPORARY) --- */}
      <div className="alert alert-info">
        <strong>除錯資訊:</strong><br />
        當前環境 (MODE): {import.meta.env.MODE}<br />
        使用的 API 位址 (apiBaseUrl): {apiBaseUrl}
      </div>
      {/* --- END DEBUGGING INFO --- */}

      {loading && <p className="text-center">載入中...</p>}
      
      {error && (
        <div className="alert alert-danger">
          <p className="text-center text-danger">讀取作品失敗，請將以下錯誤訊息回報給開發者：</p>
          <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
            {JSON.stringify({ message: error.message, stack: error.stack }, null, 2)}
          </pre>
        </div>
      )}
      
      {!loading && !error && items.length === 0 && (
        <p className="text-center">目前沒有任何作品。</p>
      )}

      {!loading && !error && items.length > 0 && (
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
