import React from 'react';

const Home: React.FC = () => {
  return (
    <div className="container text-center mt-5">
      <h1 className="display-3">歡迎來到 GF Motor</h1>
      <p className="lead">您最專業的機車夥伴</p>
      <div 
        style={{
          height: '400px', 
          background: `url('https://via.placeholder.com/1200x400/000000/FFFFFF?text=Awesome+Motorcycle+Image') no-repeat center center/cover`,
          borderRadius: '8px',
          marginTop: '30px'
        }}
        aria-label="A cool motorcycle"
      >
      </div>
      <div className="mt-5">
        <h2>我們的服務</h2>
        <p>從日常保養到深度改裝，我們無所不包。</p>
        {/* Future service cards will go here */}
      </div>
    </div>
  );
};

export default Home;
