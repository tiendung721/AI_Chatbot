"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, localDate } from "@/lib/api";
import { locationLabel, type Locator } from "@/lib/locator";
import { useKnowledgeQuery } from "./knowledge-query";

export type KnowledgeDoc = {
  id: string;
  title: string;
  version_id: string;
  number: number;
  approved_for_public: boolean;
  revoked_at: string | null;
  purged_at: string | null;
  created_at: string;
  updated_at: string;
  parse_status: string;
  scan_status: string;
  job_id: string | null;
  progress: number | null;
  error_code: string | null;
};
type Section = {
  id: string;
  ordinal: number;
  locator: Locator;
  body: string;
  review_text: string | null;
  warnings: string[];
  hidden: boolean;
  selected: boolean;
};
type Version = {
  id: string;
  document_id: string;
  number: number;
  sha256: string;
  supersedes_version_id: string | null;
  title: string;
  parse_status: string;
  scan_status: string;
  extraction_revision: number;
  sections: Section[];
  metadata_json: { warnings?: string[] };
  body: string;
  effective_from: string | null;
  effective_to: string | null;
  published: boolean;
  original_filename: string | null;
  purged_at: string | null;
  revoked_at: string | null;
};
const states: Record<string, string> = {
  uploaded: "Đã nhận file",
  scanning: "Đang quét virus",
  extracting: "Đang trích xuất",
  needs_review: "Cần kiểm tra nội dung",
  indexing: "Đang lập chỉ mục",
  ready: "Sẵn sàng",
  quarantined: "Đã cách ly",
  failed: "Xử lý lỗi",
  cancelled: "Đã hủy",
  purged: "Đã xóa nội dung",
};
const waiting = new Set(["uploaded", "scanning", "extracting", "indexing"]);
export default function KnowledgeFiles({
  docs: initialDocs,
  csrf,
  onRefresh,
}: {
  docs: KnowledgeDoc[];
  csrf: string;
  onRefresh: () => Promise<void>;
}) {
  const catalog = useKnowledgeQuery(initialDocs);
  const docs = catalog.items;
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [version, setVersion] = useState<Version | null>(null),
    [selected, setSelected] = useState<string[]>([]),
    [edits, setEdits] = useState<Record<string, string>>({}),
    [ack, setAck] = useState(false);
  const [deletion, setDeletion] = useState<{
    job_id: string;
    state: string;
  } | null>(null);
  const [target, setTarget] = useState<KnowledgeDoc | null>(null);
  const picker = useRef<HTMLInputElement>(null);
  const pendingUpload = useRef<{ files: File[]; documentId: string | null; requestId: string } | null>(null);
  const [retryUpload, setRetryUpload] = useState(false);
  const [history, setHistory] = useState<{ id: string; number: number }[]>([]);
  const [historyNext, setHistoryNext] = useState<string | null>(null);
  const [textDraft, setTextDraft] = useState<string | null>(null);
  const [comparison, setComparison] = useState<{ diff: string; metadata_changes: Record<string, unknown>; truncated: boolean } | null>(null);
  const hasJobs = docs.some(
    (d) => !d.revoked_at && waiting.has(d.parse_status),
  );
  const refresh = useCallback(async () => {
    await onRefresh();
    await catalog.reload();
  }, [onRefresh, catalog.reload]);
  useEffect(() => {
    if (!hasJobs && !deletion) return;
    let active = true,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        await refresh();
        if (deletion && !["completed", "failed"].includes(deletion.state)) {
          const job = await api<{ state: string; error_code: string | null }>(
            `/admin/knowledge/deletions/${deletion.job_id}`,
          );
          if (active && ["completed", "failed"].includes(job.state)) {
            setDeletion(null);
            setNotice(
              job.state === "completed"
                ? "Đã xóa file và nội dung dẫn xuất khỏi kho đang hoạt động."
                : "Xóa chưa hoàn tất. Bấm Xóa dữ liệu để thử lại.",
            );
          }
        }
      } catch (e) {
        if (active)
          setError(e instanceof Error ? e.message : "Không tải được tiến độ.");
      }
      if (active) timer = setTimeout(poll, 2500);
    }
    timer = setTimeout(poll, 1500);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [hasJobs, deletion, refresh]);
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Thao tác chưa hoàn tất.");
    } finally {
      setBusy(false);
    }
  }
  async function upload(files: FileList | File[] | null) {
    const chosen = Array.from(files ?? []);
    if (!chosen.length) return;
    await perform(async () => {
      if (chosen.length > 10 || (target && chosen.length !== 1))
        throw new Error("Chọn tối đa 10 file; phiên bản mới nhận một file.");
      if (chosen.some((f) => f.size > 25 * 1024 * 1024))
        throw new Error("Mỗi file tối đa 25 MB.");
      const body = new FormData();
      const documentId = target?.id ?? null;
      if (!pendingUpload.current || pendingUpload.current.documentId !== documentId ||
          chosen.some((f, i) => pendingUpload.current?.files[i] !== f) || chosen.length !== pendingUpload.current.files.length)
        pendingUpload.current = { files: chosen, documentId, requestId: crypto.randomUUID() };
      body.append("client_request_id", pendingUpload.current.requestId);
      chosen.forEach((f) => body.append("files", f));
      if (target) body.append("document_id", target.id);
      const result = await api<{
        items: { filename: string; state: string; error_code: string | null }[];
      }>("/admin/knowledge/uploads", { method: "POST", body }, csrf);
      const rejected = result.items.filter((x) => x.state === "rejected");
      setRetryUpload(rejected.length > 0);
      if (!rejected.length) pendingUpload.current = null;
      setNotice(
        `Đã nhận ${result.items.length - rejected.length}/${result.items.length} file. File cần quét sạch và trích xuất trước khi sử dụng.`,
      );
      if (rejected.length)
        setError(
          rejected.map((x) => `${x.filename}: ${x.error_code}`).join("; "),
        );
      if (!rejected.length) setTarget(null);
      await refresh();
    });
    if (pendingUpload.current) setRetryUpload(true);
    if (picker.current) picker.current.value = "";
  }
  async function open(d: KnowledgeDoc) {
    await perform(async () => {
      const v = await api<Version>(`/admin/knowledge/versions/${d.version_id}`);
      setVersion(v);
      setComparison(null);
      const detail = await api<{ versions: { id: string; number: number }[]; next_cursor: string | null }>(`/admin/knowledge/documents/${d.id}`);
      setHistory(detail.versions);
      setHistoryNext(detail.next_cursor);
      setTextDraft(null);
      setSelected(v.sections.filter((s) => s.selected).map((s) => s.id));
      setEdits({});
      setAck(false);
    });
  }
  const visibleWarnings = version
    ? [
        ...new Set([
          ...(version.metadata_json.warnings ?? []),
          ...version.sections.flatMap((s) => s.warnings),
        ]),
      ]
    : [];
  return (
    <section className="card knowledge-files">
      <div className="card-heading">
        <div>
          <h2>Kho tri thức</h2>
          <p>{catalog.total} phiên bản tài liệu</p>
        </div>
        <span className="section-icon">▤</span>
      </div>
      {catalog.controls}
      <div className="upload-panel">
        <strong>
          {target ? `Thêm phiên bản cho: ${target.title}` : "Tải tài liệu lên"}
        </strong>
        <p>
          PDF, DOCX, XLSX, PPTX, TXT, MD, CSV, HTML, PNG, JPG. Tối đa 25 MB/file
          và 10 file/lượt.
        </p>
        <label className="file-label">
          Chọn file
          <input
            ref={picker}
            type="file"
            aria-label="Tải tài liệu tri thức"
            multiple={!target}
            accept=".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,.html,.png,.jpg,.jpeg"
            disabled={busy}
            onChange={(e) => void upload(e.target.files)}
          />
        </label>
        {target && (
          <button className="text-button" onClick={() => setTarget(null)}>
            Hủy thêm phiên bản
          </button>
        )}
        {retryUpload && pendingUpload.current && <button type="button" className="button secondary small" disabled={busy} onClick={() => void upload(pendingUpload.current?.files ?? null)}>Thử lại lượt tải</button>}
        <p className="subtle">
          File chỉ là nguồn dữ liệu. Các chỉ dẫn nằm trong tài liệu không thay
          thế cấu hình trợ lý.
        </p>
      </div>
      {catalog.pagination}
      {error && (
        <div className="alert error" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      {deletion && (
        <p role="status">Đang xóa dữ liệu… Tài liệu đã được thu hồi ngay.</p>
      )}
      <div className="document-list">
        {docs.map((d) => (
          <article className="document-row" key={d.version_id}>
            <span className="doc-icon">▤</span>
            <div>
              <strong>{d.title}</strong>
              <p>
                V{d.number} · {localDate(d.updated_at ?? d.created_at)}
              </p>
              <span
                className={`badge ${d.revoked_at ? "amber" : d.approved_for_public ? "teal" : "neutral"}`}
              >
                {d.purged_at
                  ? "Đã xóa nội dung"
                  : d.revoked_at
                    ? "Đã thu hồi"
                    : d.approved_for_public
                      ? "Đã xác nhận công khai"
                      : (states[d.parse_status] ?? d.parse_status)}
              </span>
              {waiting.has(d.parse_status) && !d.revoked_at && (
                <progress
                  aria-label={`Tiến độ ${d.title}`}
                  value={d.progress ?? 0}
                  max={100}
                />
              )}
              {d.error_code && <p role="status">Mã lỗi: {d.error_code}</p>}
            </div>
            <div className="row-actions">
              {!d.purged_at && (
                <button
                  className="text-button"
                  disabled={busy}
                  onClick={() => void open(d)}
                >
                  Xem nội dung
                </button>
              )}
              {d.parse_status === "failed" && !d.revoked_at && d.job_id && (
                <button
                  className="button secondary small"
                  disabled={busy}
                  onClick={() =>
                    void perform(async () => {
                      await api(
                        `/admin/knowledge/jobs/${d.job_id}/retry`,
                        { method: "POST" },
                        csrf,
                      );
                      await refresh();
                    })
                  }
                >
                  Thử lại xử lý
                </button>
              )}
              {d.parse_status === "ready" &&
                !d.revoked_at &&
                !d.approved_for_public && (
                  <button
                    className="button secondary small"
                    disabled={busy}
                    onClick={() => {
                      if (
                        window.confirm(
                          "Xác nhận tài liệu được phép công khai và không chứa dữ liệu cá nhân chưa được phép công bố?",
                        )
                      )
                        void perform(async () => {
                          await api(
                            `/admin/knowledge/versions/${d.version_id}/approve-public`,
                            {
                              method: "POST",
                              body: JSON.stringify({ confirm_public: true }),
                            },
                            csrf,
                          );
                          await refresh();
                          setNotice(
                            "Đã xác nhận công khai. Chọn phiên bản trong bản nháp, lưu và xuất bản để công dân sử dụng.",
                          );
                        });
                    }}
                  >
                    Xác nhận công khai
                  </button>
                )}
              {!d.revoked_at && (
                <>
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => {
                      setTarget(d);
                      picker.current?.focus();
                    }}
                  >
                    Thêm phiên bản file
                  </button>
                  <button
                    className="text-button danger"
                    disabled={busy}
                    onClick={() => {
                      const reason = window.prompt(
                        "Lý do thu hồi ngay tài liệu (ít nhất 3 ký tự):",
                      );
                      if (reason)
                        void perform(async () => {
                          await api(
                            `/admin/knowledge/documents/${d.id}/revoke`,
                            {
                              method: "POST",
                              body: JSON.stringify({ reason }),
                            },
                            csrf,
                          );
                          setVersion(null);
                          await refresh();
                        });
                    }}
                  >
                    Thu hồi
                  </button>
                </>
              )}
              {!d.purged_at && (
                <button
                  className="text-button danger"
                  disabled={busy}
                  onClick={() => {
                    const reason = window.prompt(
                      "Xóa file và nội dung dẫn xuất khỏi kho đang hoạt động. Không thể hoàn tác. Nhập lý do (ít nhất 3 ký tự):",
                    );
                    if (reason)
                      void perform(async () => {
                        const r = await api<{ job_id: string; state: string }>(
                          `/admin/knowledge/documents/${d.id}/delete-request`,
                          { method: "POST", body: JSON.stringify({ reason }) },
                          csrf,
                        );
                        if (r.state !== "completed") setDeletion(r);
                        setVersion(null);
                        await refresh();
                      });
                  }}
                >
                  Xóa dữ liệu
                </button>
              )}
            </div>
          </article>
        ))}
        {!docs.length && (
          <div className="empty-state">
            Tải file hoặc soạn văn bản đầu tiên để xây dựng kho tri thức.
          </div>
        )}
      </div>
      {version && (
        <div
          className="extraction-panel"
          role="region"
          aria-label="Kiểm tra bản trích xuất"
        >
          <div className="card-heading">
            <div>
              <h3>{version.title}</h3>
              <p>
                {states[version.parse_status]} · {version.sections.length} phần
              </p>
            </div>
            <button className="text-button" onClick={() => setVersion(null)}>
              Đóng bản trích xuất
            </button>
          </div>
          {version.published ? (
            <p className="notice">
              Phiên bản đã xuất bản được giữ nguyên. Để đổi nội dung hoặc hiệu
              lực, hãy thêm phiên bản mới.
            </p>
          ) : (
            !version.revoked_at &&
            ["ready", "needs_review"].includes(version.parse_status) && (
              <VersionMetadata
                key={version.id}
                version={version}
                versions={history.filter((h) => h.number < version.number)}
                csrf={csrf}
                onSaved={async () => {
                  setVersion(
                    await api<Version>(
                      `/admin/knowledge/versions/${version.id}`,
                    ),
                  );
                  await refresh();
                }}
              />
            )
          )}
          <details><summary>Thông tin đối chiếu file</summary><p className="subtle">SHA256: {version.sha256}</p></details>
          {historyNext && <button type="button" className="text-button" disabled={busy} onClick={() => void perform(async () => {
            const detail = await api<{ versions: { id: string; number: number }[]; next_cursor: string | null }>(`/admin/knowledge/documents/${version.document_id}?page=${historyNext}`);
            setHistory((items) => [...new Map([...items, ...detail.versions].map((v) => [v.id, v])).values()]);
            setHistoryNext(detail.next_cursor);
          })}>Tải thêm phiên bản để so sánh</button>}
          {history.length > 1 && <label>So sánh với phiên bản
            <select aria-label="So sánh với phiên bản" defaultValue="" onChange={(e) => {
              const against = e.target.value;
              if (against) void perform(async () => setComparison(await api(`/admin/knowledge/versions/${version.id}/diff?against=${against}`)));
              else setComparison(null);
            }}><option value="">Chọn phiên bản</option>{history.filter((h) => h.id !== version.id).map((h) => <option key={h.id} value={h.id}>V{h.number}</option>)}</select>
          </label>}
          {comparison && <div role="region" aria-label="Đối chiếu phiên bản"><pre className="plain-source">{comparison.diff || "Không thay đổi nội dung trích xuất."}</pre><MetadataChanges changes={comparison.metadata_changes} versions={history} />{comparison.truncated && <p role="status">Bản so sánh đã rút gọn do giới hạn hiển thị. Kiểm tra thêm file gốc.</p>}</div>}
          {version.sections.length === 0 && version.body && (
            <pre className="plain-source">{version.body}</pre>
          )}
          {!version.revoked_at && version.body.length <= 100000 && <details className="extraction-section"><summary>Tạo phiên bản văn bản mới</summary>
            <p>Phiên bản mới chưa được xác nhận công khai. Bản đang hoạt động giữ nguyên.</p>
            <textarea aria-label="Nội dung phiên bản văn bản mới" value={textDraft ?? version.body} maxLength={100000} rows={8} onChange={(e) => setTextDraft(e.target.value)} />
            <button type="button" className="button secondary small" disabled={busy || !(textDraft ?? version.body).trim()} onClick={() => void perform(async () => {
              const result = await api<{ version_id: string }>(`/admin/knowledge/documents/${version.document_id}/versions`, { method: "POST", body: JSON.stringify({ title: version.title, body: textDraft ?? version.body }) }, csrf);
              setVersion(await api<Version>(`/admin/knowledge/versions/${result.version_id}`));
              setTextDraft(null); setComparison(null);
              const detail = await api<{ versions: { id: string; number: number }[]; next_cursor: string | null }>(`/admin/knowledge/documents/${version.document_id}`);
              setHistory(detail.versions); setHistoryNext(detail.next_cursor);
              await refresh(); setNotice("Đã tạo phiên bản văn bản mới. Kiểm tra metadata và xác nhận công khai trước khi xuất bản.");
            })}>Tạo phiên bản văn bản</button>
          </details>}
          {version.original_filename &&
            version.scan_status === "clean" &&
            !version.revoked_at && (
              <a
                className="text-button"
                href={`/api/v1/admin/knowledge/versions/${version.id}/original`}
              >
                Tải file gốc đã quét sạch
              </a>
            )}
          {visibleWarnings.length > 0 && (
            <div className="notice">
              <strong>Cần kiểm tra</strong>
              <p>
                OCR có thể sai chữ; sheet ẩn mặc định không được chọn. Công thức
                Excel chỉ đọc kết quả đã lưu; không tự tính lại.
              </p>
              <ul>
                {visibleWarnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}
          {version.sections.map((s) => (
            <details
              key={s.id}
              className="extraction-section"
              open={version.sections.length === 1}
            >
              <summary>
                {locationLabel(s.locator, s.ordinal)}
                {s.hidden ? " · Sheet ẩn" : ""}
              </summary>
              {!version.published && !version.revoked_at && ["needs_review", "ready"].includes(version.parse_status) ? (
                <>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={selected.includes(s.id)}
                      onChange={(e) =>
                        setSelected((a) =>
                          e.target.checked
                            ? [...a, s.id]
                            : a.filter((id) => id !== s.id),
                        )
                      }
                    />
                    Đưa phần này vào tri thức
                  </label>
                  <label>
                    Nội dung trích xuất
                    <textarea
                      aria-label={`Nội dung phần ${s.ordinal}`}
                      value={edits[s.id] ?? s.review_text ?? s.body}
                      rows={8}
                      maxLength={1000000}
                      disabled={!selected.includes(s.id)}
                      onChange={(e) =>
                        setEdits((a) => ({ ...a, [s.id]: e.target.value }))
                      }
                    />
                  </label>
                </>
              ) : (
                <pre>{s.review_text ?? s.body}</pre>
              )}
              {s.warnings.length > 0 && (
                <p className="subtle">{s.warnings.join(" · ")}</p>
              )}
            </details>
          ))}
          {["needs_review", "ready"].includes(version.parse_status) && version.sections.length > 0 && !version.published && !version.revoked_at && (
            <>
              <label className="check-row">
                <input
                  type="checkbox"
                  checked={ack}
                  onChange={(e) => setAck(e.target.checked)}
                />
                Tôi đã kiểm tra cảnh báo và nội dung được chọn.
              </label>
              <button
                className="button primary"
                disabled={busy || !ack || !selected.length}
                onClick={() =>
                  void perform(async () => {
                    await api(
                      `/admin/knowledge/versions/${version.id}/review`,
                      {
                        method: "POST",
                        body: JSON.stringify({
                          revision: version.extraction_revision,
                          selected_section_ids: selected,
                          edits: Object.entries(edits)
                            .filter(([id]) => selected.includes(id))
                            .map(([section_id, text]) => ({
                              section_id,
                              text,
                            })),
                          acknowledge_warnings: ack,
                        }),
                      },
                      csrf,
                    );
                    setVersion(null);
                    await refresh();
                    setNotice(
                      "Đã duyệt trích xuất và tạo chỉ mục. Bạn vẫn cần xác nhận công khai trước khi xuất bản.",
                    );
                  })
                }
              >
                Duyệt nội dung và lập chỉ mục
              </button>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function MetadataChanges({ changes, versions }: { changes: Record<string, unknown>; versions: { id: string; number: number }[] }) {
  const labels: Record<string, string> = { document_number: "Số văn bản", issuer: "Cơ quan ban hành", issued_on: "Ngày ban hành", effective_from: "Có hiệu lực từ", effective_to: "Hết hiệu lực", source_url: "Trang công bố", source_collected_on: "Ngày thu thập", jurisdiction: "Phạm vi áp dụng", classification: "Phân loại dữ liệu", topic_tags: "Nhãn chủ đề", allow_public_download: "Quyền tải file gốc", supersedes_version_id: "Phiên bản được thay thế" };
  function display(key: string, value: unknown): string {
    if (value === null || value === undefined || value === "") return "Chưa có";
    if (Array.isArray(value)) return value.length ? value.join(", ") : "Chưa có";
    if (typeof value === "boolean") return value ? "Cho phép" : "Không cho phép";
    if (key === "supersedes_version_id") { const version = versions.find((v) => v.id === value); return version ? `Phiên bản ${version.number}` : "Phiên bản đã liên kết"; }
    const names: Record<string, string> = { public: "Công khai sau duyệt", internal: "Nội bộ", restricted: "Hạn chế", national: "Toàn quốc", current_tenant: "Đơn vị hiện tại" };
    return names[String(value)] ?? String(value);
  }
  const entries = Object.entries(changes).filter(([key]) => labels[key]);
  if (!entries.length) return null;
  return <div className="metadata-changes"><h4>Thông tin đã thay đổi</h4>{entries.map(([key, raw]) => {
    const value = raw as { before?: unknown; after?: unknown };
    return <div key={key}><strong>{labels[key]}</strong><p>Trước: {display(key, value.before)}</p><p>Sau: {display(key, value.after)}</p></div>;
  })}</div>;
}

function VersionMetadata({
  version,
  versions,
  csrf,
  onSaved,
}: {
  version: Version;
  versions: { id: string; number: number }[];
  csrf: string;
  onSaved: () => Promise<void>;
}) {
  const meta = version.metadata_json as Record<string, unknown>;
  const [number, setNumber] = useState(String(meta.document_number ?? "")),
    [issuer, setIssuer] = useState(String(meta.issuer ?? ""));
  const [issued, setIssued] = useState(String(meta.issued_on ?? "")),
    [from, setFrom] = useState(version.effective_from ?? ""),
    [to, setTo] = useState(version.effective_to ?? "");
  const [sourceUrl, setSourceUrl] = useState(String(meta.source_url ?? "")),
    [collected, setCollected] = useState(String(meta.source_collected_on ?? "")),
    [jurisdiction, setJurisdiction] = useState(String(meta.jurisdiction ?? "current_tenant")),
    [classification, setClassification] = useState(String(meta.classification ?? "public")),
    [tags, setTags] = useState((Array.isArray(meta.topic_tags) ? meta.topic_tags : []).join(", ")),
    [previous, setPrevious] = useState(version.supersedes_version_id ?? "");
  const [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  return (
    <form
      className="metadata-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setMessage("");
        try {
          await api(
            `/admin/knowledge/versions/${version.id}/metadata`,
            {
              method: "PATCH",
              body: JSON.stringify({
                revision: version.extraction_revision,
                document_number: number,
                issuer,
                issued_on: issued || null,
                effective_from: from || null,
                effective_to: to || null,
                source_url: sourceUrl || null,
                source_collected_on: collected || null,
                jurisdiction, classification,
                topic_tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
                supersedes_version_id: previous || null,
                allow_public_download: meta.allow_public_download === true,
              }),
            },
            csrf,
          );
          await onSaved();
          setMessage(
            "Đã lưu metadata. Cần xác nhận công khai lại trước khi xuất bản.",
          );
        } catch (e) {
          setMessage(
            e instanceof Error ? e.message : "Chưa lưu được metadata.",
          );
        } finally {
          setBusy(false);
        }
      }}
    >
      <h4>Thông tin văn bản và hiệu lực</h4>
      <p className="subtle">
        Chỉ nhập ngày đã xác định từ văn bản. Để trống nếu chưa rõ; ngày tải lên
        không phải ngày hiệu lực.
      </p>
      <label>
        Số văn bản
        <input
          value={number}
          maxLength={120}
          onChange={(e) => setNumber(e.target.value)}
        />
      </label>
      <label>
        Cơ quan ban hành
        <input
          value={issuer}
          maxLength={300}
          onChange={(e) => setIssuer(e.target.value)}
        />
      </label>
      <label>
        Ngày ban hành
        <input
          type="date"
          value={issued}
          onChange={(e) => setIssued(e.target.value)}
        />
      </label>
      <label>
        Có hiệu lực từ
        <input
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
        />
      </label>
      <label>
        Hết hiệu lực ngày
        <input
          type="date"
          value={to}
          min={from || undefined}
          onChange={(e) => setTo(e.target.value)}
        />
      </label>
      <label>URL trang công bố<input type="url" value={sourceUrl} maxLength={2048} onChange={(e) => setSourceUrl(e.target.value)} /></label>
      <label>Ngày thu thập<input type="date" value={collected} onChange={(e) => setCollected(e.target.value)} /></label>
      <label>Phạm vi áp dụng<select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}><option value="current_tenant">Đơn vị hiện tại</option><option value="national">Toàn quốc</option></select></label>
      <label>Phân loại dữ liệu<select value={classification} onChange={(e) => setClassification(e.target.value)}><option value="public">Được phép công khai sau duyệt</option><option value="internal">Nội bộ</option><option value="restricted">Hạn chế</option></select></label>
      <label>Nhãn chủ đề, phân cách bằng dấu phẩy<input value={tags} maxLength={1620} onChange={(e) => setTags(e.target.value)} /></label>
      <label>Thay thế phiên bản<select value={previous} onChange={(e) => setPrevious(e.target.value)}><option value="">Không chỉ định</option>{previous && !versions.some((v) => v.id === previous) && <option value={previous}>Phiên bản đã liên kết</option>}{versions.map((v) => <option key={v.id} value={v.id}>Phiên bản {v.number}</option>)}</select></label>
      <p className="subtle">URL chỉ ghi nhận nguồn, không tự tải hoặc đồng bộ website. Nội dung nội bộ/hạn chế không được xác nhận công khai.</p>
      <button className="button secondary small" disabled={busy}>
        Lưu thông tin văn bản
      </button>
      {message && <p role="status">{message}</p>}
    </form>
  );
}
