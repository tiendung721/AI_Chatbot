import Link from "next/link";
export default function Home() {
  return (
    <main className="welcome-page">
      <div className="brand-symbol">P</div>
      <span className="eyebrow">NỀN TẢNG THÔNG TIN CÔNG DÂN</span>
      <h1>
        Tri thức của phường.
        <br />
        Gần hơn với người dân.
      </h1>
      <p>
        Quản lý nội dung, kiểm tra nguồn và xuất bản trợ lý thông tin của đơn
        vị.
      </p>
      <Link className="button primary" href="/admin">
        Mở cổng quản trị <span>↗</span>
      </Link>
      <div className="notice">
        Bản phát triển local · Chỉ sử dụng dữ liệu kiểm thử đã ghi nhãn.
      </div>
    </main>
  );
}
