"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { KnowledgeDoc } from "./knowledge-files";

export function useKnowledgeQuery(refreshKey: unknown) {
  const [q, setQ] = useState(""), [status, setStatus] = useState(""),
    [approved, setApproved] = useState(""), [fileType, setFileType] = useState(""),
    [effectivity, setEffectivity] = useState(""), [page, setPage] = useState(1);
  const [items, setItems] = useState<KnowledgeDoc[]>([]), [total, setTotal] = useState(0),
    [loading, setLoading] = useState(true), [error, setError] = useState("");
  const query = new URLSearchParams({ page: String(page), page_size: "20" });
  if (q) query.set("q", q);
  if (status) query.set("status", status);
  if (approved) query.set("approved", approved);
  if (fileType) query.set("file_type", fileType);
  if (effectivity) query.set("effectivity", effectivity);
  const url = `/admin/knowledge/documents?${query}`;
  const activeUrl = useRef(url);
  activeUrl.current = url;
  const reload = useCallback(async () => {
    const r = await api<{ items: KnowledgeDoc[]; total: number }>(url);
    if (activeUrl.current === url) { setItems(r.items); setTotal(r.total); }
  }, [url]);
  useEffect(() => {
    let active = true;
    setLoading(true); setError("");
    const timer = setTimeout(() => {
      api<{ items: KnowledgeDoc[]; total: number }>(url).then((r) => {
        if (active) { setItems(r.items); setTotal(r.total); }
      }).catch((e: unknown) => { if (active) setError(e instanceof Error ? e.message : "Không tải được kho tài liệu."); })
        .finally(() => { if (active) setLoading(false); });
    }, 200);
    return () => { active = false; clearTimeout(timer); };
  }, [url, refreshKey]);
  function change(setter: (s: string) => void, value: string) { setter(value); setPage(1); }
  const controls = <div className="catalog-controls">
    <label>Tìm tài liệu<input aria-label="Tìm tài liệu" value={q} maxLength={200} placeholder="Tên, số văn bản hoặc nhãn" onChange={(e) => change(setQ, e.target.value)} /></label>
    <label>Trạng thái<select value={status} onChange={(e) => change(setStatus, e.target.value)}>
      <option value="">Tất cả trạng thái</option><option value="ready">Sẵn sàng</option><option value="needs_review">Cần duyệt</option><option value="failed">Lỗi</option><option value="quarantined">Cách ly</option><option value="revoked">Thu hồi</option><option value="purged">Đã xóa</option>
    </select></label>
    <label>Công khai<select value={approved} onChange={(e) => change(setApproved, e.target.value)}><option value="">Tất cả</option><option value="true">Đã xác nhận</option><option value="false">Chưa xác nhận</option></select></label>
    <label>Định dạng<select value={fileType} onChange={(e) => change(setFileType, e.target.value)}><option value="">Tất cả định dạng</option>{["text", "pdf", "docx", "xlsx", "pptx", "txt", "md", "csv", "html", "png", "jpg"].map((v) => <option key={v} value={v}>{v === "text" ? "Văn bản nhập" : v.toUpperCase()}</option>)}</select></label>
    <label>Hiệu lực<select value={effectivity} onChange={(e) => change(setEffectivity, e.target.value)}><option value="">Tất cả</option><option value="active">Trong khoảng hiệu lực</option><option value="future">Chưa hiệu lực</option><option value="expired">Hết hiệu lực</option><option value="unknown">Chưa rõ ngày</option></select></label>
    {loading && <p role="status">Đang tải tài liệu…</p>}{error && <p role="alert">{error}</p>}
  </div>;
  const pagination = <div className="catalog-pagination">
    <button type="button" className="button secondary small" disabled={page <= 1 || loading} onClick={() => setPage((p) => p - 1)}>Trang trước</button>
    <span role="status">Trang {page} / {Math.max(1, Math.ceil(total / 20))} · {total} phiên bản</span>
    <button type="button" className="button secondary small" disabled={page * 20 >= total || loading} onClick={() => setPage((p) => p + 1)}>Trang sau</button>
  </div>;
  return { items, controls, pagination, reload, loading, total };
}

export default function KnowledgePicker({ selected, onChange, refreshKey }: {
  selected: string[]; onChange: (ids: string[]) => void; refreshKey: unknown;
}) {
  const catalog = useKnowledgeQuery(refreshKey);
  return <>{catalog.controls}<p>{selected.length} phiên bản đã chọn trên toàn bộ kho. Đổi trang không bỏ lựa chọn.</p>
    {catalog.items.map((d) => <label className="document-choice" key={d.version_id}>
      <input type="checkbox" checked={selected.includes(d.version_id)} disabled={catalog.loading || (!selected.includes(d.version_id) && (!!d.revoked_at || d.parse_status !== "ready"))}
        onChange={(e) => onChange(e.target.checked ? [...selected, d.version_id] : selected.filter((id) => id !== d.version_id))} />
      <span className="doc-icon">▤</span><div><strong>{d.title}</strong><small>Phiên bản {d.number} · {d.revoked_at ? "Đã thu hồi" : d.approved_for_public ? "Đã xác nhận công khai" : "Chờ xác nhận công khai"}</small></div>
    </label>)}{catalog.pagination}</>;
}
