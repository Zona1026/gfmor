function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-surface text-center text-white p-3 mt-auto">
      <div className="container">
        <p className="mb-0">&copy; {currentYear} GF Motor. All Rights Reserved.</p>
      </div>
    </footer>
  );
}

export default Footer;
