"use client";
import { FormEvent, useCallback, useEffect, useState } from "react";
import Chat from "@/components/chat";
import KnowledgePicker from "@/components/knowledge-query";
import KnowledgeFiles, {
  type KnowledgeDoc,
} from "@/components/knowledge-files";
import {
  api,
  ApiError,
  localDate,
  type AdminView,
  type AssistantConfig,
} from "@/lib/api";

type Doc = KnowledgeDoc;
type Release = {
  id: string;
  sequence: number;
  reason: string;
  created_at: string;
};
type Profile = {
  email: string;
  csrf_token: string;
  must_change_password: boolean;
};
type Nav = "overview" | "builder" | "knowledge" | "releases";
const navigation: { id: Nav; label: string; icon: string }[] = [
  { id: "overview", label: "Tổng quan", icon: "◫" },
  { id: "builder", label: "Cấu hình chatbot", icon: "✦" },
  { id: "knowledge", label: "Kho tri thức", icon: "▤" },
  { id: "releases", label: "Kiểm tra & xuất bản", icon: "⇧" },
];

export default function AdminPage() {
  const [profile, setProfile] = useState<Profile | null>(null),
    [view, setView] = useState<AdminView | null>(null),
    [config, setConfig] = useState<AssistantConfig | null>(null);
  const [docs, setDocs] = useState<Doc[]>([]),
    [releases, setReleases] = useState<Release[]>([]),
    [nav, setNav] = useState<Nav>("builder");
  const [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true);
  const [textTitle, setTextTitle] = useState(""),
    [textBody, setTextBody] = useState("");
  const [preflight, setPreflight] = useState<{
    validation_id: string;
    checks: string[];
  } | null>(null);
  const [dirty, setDirty] = useState(false),
    [reason, setReason] = useState("");
  const [auditItems, setAuditItems] = useState<
    { event_type: string; created_at: string }[]
  >([]);
  const [dashboard, setDashboard] = useState<{
    documents: { n: number };
    turns: { n: number };
    paused: boolean;
  } | null>(null);
  const load = useCallback(async () => {
    const [v, d, r] = await Promise.all([
      api<AdminView>("/admin/assistant"),
      api<{ items: Doc[] }>("/admin/knowledge/documents"),
      api<{ items: Release[] }>("/admin/releases"),
    ]);
    setView(v);
    setConfig(v.config);
    setDocs(d.items);
    setReleases(r.items);
    setDirty(false);
    setPreflight(null);
  }, []);
  const refreshDocs = useCallback(async () => {
    const r = await api<{ items: Doc[] }>("/admin/knowledge/documents");
    setDocs(r.items);
    setPreflight(null);
  }, []);
  useEffect(() => {
    api<Profile>("/auth/me")
      .then(async (p) => {
        setProfile(p);
        if (!p.must_change_password) await load();
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, [load]);
  useEffect(() => {
    if (!profile || profile.must_change_password || nav !== "overview") return;
    api<{ items: { event_type: string; created_at: string }[] }>("/admin/audit")
      .then((r) => setAuditItems(r.items))
      .catch((e) => setError(e.message));
    api<{ documents: { n: number }; turns: { n: number }; paused: boolean }>(
      "/admin/dashboard",
    )
      .then(setDashboard)
      .catch((e) => setError(e.message));
  }, [nav, profile]);
  useEffect(() => {
    function leaving(e: BeforeUnloadEvent) {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    }
    window.addEventListener("beforeunload", leaving);
    return () => window.removeEventListener("beforeunload", leaving);
  }, [dirty]);
  async function perform(action: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Yêu cầu chưa hoàn tất.");
      if (e instanceof ApiError && e.status === 401) setProfile(null);
    } finally {
      setBusy(false);
    }
  }
  async function login(e: FormEvent) {
    e.preventDefault();
    await perform(async () => {
      const r = await api<{
        csrf_token: string;
        must_change_password: boolean;
      }>("/auth/admin/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      setProfile({ ...r, email });
      if (!r.must_change_password) {
        await load();
        setPassword("");
      }
    });
  }
  async function changePassword(e: FormEvent) {
    e.preventDefault();
    await perform(async () => {
      await api(
        "/auth/admin/change-password",
        {
          method: "POST",
          body: JSON.stringify({
            current_password: password,
            new_password: newPassword,
          }),
        },
        profile?.csrf_token,
      );
      setProfile((p) => (p ? { ...p, must_change_password: false } : null));
      setPassword("");
      setNewPassword("");
      await load();
    });
  }
  function update(patch: Partial<AssistantConfig>) {
    setConfig((c) => (c ? { ...c, ...patch } : c));
    setDirty(true);
    setPreflight(null);
  }
  async function save() {
    if (!view || !config) return;
    await perform(async () => {
      const r = await api<{ revision: number }>(
        "/admin/assistant/draft",
        {
          method: "PATCH",
          headers: { "If-Match": `"${view.revision}"` },
          body: JSON.stringify(config),
        },
        profile?.csrf_token,
      );
      setView({ ...view, revision: r.revision, config });
      setDirty(false);
      setPreflight(null);
      setNotice("Đã lưu bản nháp. Nội dung đang hoạt động chưa thay đổi.");
    });
  }
  async function addText(e: FormEvent) {
    e.preventDefault();
    await perform(async () => {
      await api(
        "/admin/knowledge/texts",
        {
          method: "POST",
          body: JSON.stringify({ title: textTitle, body: textBody }),
        },
        profile?.csrf_token,
      );
      const r = await api<{ items: Doc[] }>("/admin/knowledge/documents");
      setDocs(r.items);
      setTextTitle("");
      setTextBody("");
      setNotice(
        "Đã xử lý văn bản. Hãy xác nhận công khai rồi chọn tài liệu trong bản nháp.",
      );
    });
  }

  if (loading)
    return (
      <main className="welcome-page" role="status">
        <span className="spinner" />
        Đang kiểm tra phiên đăng nhập…
      </main>
    );
  if (!profile || profile.must_change_password)
    return (
      <main className="login-page">
        <section className="login-intro">
          <div className="brand-lockup">
            <span className="brand-symbol">P</span>
            <strong>Trợ lý thông tin phường</strong>
          </div>
          <span className="eyebrow">CỔNG QUẢN TRỊ NỘI DUNG</span>
          <h1>
            Thông tin rõ ràng.
            <br />
            Phục vụ gần gũi.
          </h1>
          <p>
            Một nơi để quản lý tri thức, kiểm tra câu trả lời và xuất bản trợ lý
            của đơn vị.
          </p>
          <div className="intro-card">
            <span>▤</span>
            <div>
              <strong>Tri thức được kiểm soát</strong>
              <p>
                Bản nháp, nguồn dẫn và phiên bản xuất bản được quản lý riêng.
              </p>
            </div>
          </div>
          <small>PHIÊN BẢN PHÁT TRIỂN · KHÔNG NHẬP HỒ SƠ THẬT</small>
        </section>
        <section className="login-form-wrap">
          <form
            className="login-form"
            onSubmit={profile ? changePassword : login}
          >
            <span className="eyebrow">CHÀO MỪNG TRỞ LẠI</span>
            <h2>{profile ? "Đổi mật khẩu lần đầu" : "Đăng nhập quản trị"}</h2>
            <p className="subtle">
              {profile
                ? "Đặt mật khẩu riêng trước khi quản lý nội dung."
                : "Sử dụng tài khoản được cấp cho phường của bạn."}
            </p>
            {!profile && (
              <label>
                Email
                <input
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ten@donvi.vn"
                />
              </label>
            )}
            <label>
              {profile ? "Mật khẩu được cấp" : "Mật khẩu"}
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {profile && (
              <label>
                Mật khẩu mới
                <input
                  type="password"
                  autoComplete="new-password"
                  minLength={14}
                  maxLength={256}
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
                <small>Ít nhất 14 ký tự.</small>
              </label>
            )}
            {error && (
              <div className="notice error" role="alert">
                {error}
              </div>
            )}
            <button
              type="submit"
              className="button primary full"
              disabled={busy}
            >
              {busy
                ? "Đang xử lý…"
                : profile
                  ? "Lưu mật khẩu mới"
                  : "Đăng nhập"}
              <span aria-hidden="true">→</span>
            </button>
            <div className="login-help">
              Tài khoản local được cấp qua bootstrap. Xem file{" "}
              <code>.local/provisioned-admins.json</code> trên máy của bạn.
            </div>
          </form>
        </section>
      </main>
    );
  if (!view || !config)
    return (
      <main className="welcome-page">
        <p role="alert">{error || "Chưa tải được cấu hình."}</p>
        <button onClick={() => perform(load)}>Tải lại</button>
      </main>
    );
  const header = navigation.find((n) => n.id === nav)!;
  return (
    <div className="admin-shell">
      <aside className="sidebar">
        <a className="brand-lockup" href="/admin">
          <span className="brand-symbol">P</span>
          <div>
            <strong>Cổng quản trị</strong>
            <small>Trợ lý thông tin phường</small>
          </div>
        </a>
        <div className="tenant-card">
          <span className="tenant-icon">▧</span>
          <div>
            <span className="eyebrow">ĐƠN VỊ CỦA BẠN</span>
            <strong>{view.tenant_name}</strong>
          </div>
        </div>
        <span className="nav-caption">KHÔNG GIAN LÀM VIỆC</span>
        <nav>
          {navigation.map((n) => (
            <button
              key={n.id}
              onClick={() => setNav(n.id)}
              className={nav === n.id ? "nav-item active" : "nav-item"}
            >
              <span>{n.icon}</span>
              {n.label}
              {nav === n.id && <i />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="badge teal">● Phiên bản phát triển</span>
          <div className="account-row">
            <span className="account-avatar">A</span>
            <div>
              <strong>Quản trị viên</strong>
              <small>{profile.email}</small>
            </div>
          </div>
          <button
            className="text-button"
            onClick={() =>
              perform(async () => {
                await api(
                  "/auth/logout",
                  { method: "POST" },
                  profile.csrf_token,
                );
                setProfile(null);
                setView(null);
              })
            }
          >
            Đăng xuất ↗
          </button>
        </div>
      </aside>
      <div className="admin-main">
        <header className="topbar">
          <div>
            <span className="subtle">Không gian làm việc</span>
            <span className="breadcrumb">/</span>
            <strong>{header.label}</strong>
          </div>
          <a
            className="button secondary small"
            href={`/chat/${view.public_key}`}
            target="_blank"
            rel="noreferrer"
          >
            Mở trang công dân ↗
          </a>
        </header>
        <main className="admin-content">
          <div className="page-heading">
            <div>
              <span className="eyebrow">QUẢN LÝ TRỢ LÝ</span>
              <h1>{header.label}</h1>
              <p>
                {nav === "builder"
                  ? "Thiết lập cách trợ lý giao tiếp và chọn tri thức để trả lời."
                  : nav === "knowledge"
                    ? "Chuẩn bị nội dung có nguồn trước khi đưa đến người dân."
                    : "Theo dõi nội dung trong phạm vi đơn vị của bạn."}
              </p>
            </div>
            <span className={`badge ${dirty ? "amber" : "teal"}`}>
              {dirty
                ? "● Có thay đổi chưa lưu"
                : `● Bản nháp #${view.revision}`}
            </span>
          </div>
          {(error || notice) && (
            <div
              className={`notice ${error ? "error" : "success"}`}
              role={error ? "alert" : "status"}
            >
              {error || notice}
            </div>
          )}
          {view.testing && (
            <div className="environment-note">
              <span>◈</span> Môi trường thử nghiệm — chưa kết nối AI thật. Chỉ
              dùng dữ liệu giả.
            </div>
          )}
          {nav === "builder" && (
            <div className="builder-grid">
              <section className="card configure-card">
                <div className="card-heading">
                  <div>
                    <h2>Cấu hình nội dung</h2>
                    <p>Thay đổi chỉ đến người dân sau khi xuất bản.</p>
                  </div>
                  <span className="section-icon">✦</span>
                </div>
                <div className="form-section">
                  <span className="section-number">01</span>
                  <h3>Thông tin cơ bản</h3>
                  <label>
                    Tên chatbot
                    <input
                      value={config.name}
                      maxLength={120}
                      onChange={(e) => update({ name: e.target.value })}
                    />
                  </label>
                  <label>
                    Mô tả
                    <textarea
                      rows={2}
                      value={config.description}
                      maxLength={500}
                      onChange={(e) => update({ description: e.target.value })}
                    />
                  </label>
                  <label>
                    Lời chào
                    <textarea
                      rows={2}
                      value={config.welcome_message}
                      maxLength={500}
                      onChange={(e) =>
                        update({ welcome_message: e.target.value })
                      }
                    />
                  </label>
                </div>
                <div className="form-section">
                  <span className="section-number">02</span>
                  <h3>Hướng dẫn trả lời</h3>
                  <p className="subtle">
                    Định hướng cách diễn đạt và phạm vi nghiệp vụ.
                  </p>
                  <label className="sr-only" htmlFor="instructions">
                    Instructions nghiệp vụ
                  </label>
                  <textarea
                    id="instructions"
                    rows={6}
                    maxLength={12000}
                    value={config.instructions}
                    onChange={(e) => update({ instructions: e.target.value })}
                  />
                  <div className="field-meta">
                    <span>Ngắn gọn, rõ ràng, phù hợp nghiệp vụ.</span>
                    <span>
                      {config.instructions.length.toLocaleString("vi-VN")} /
                      12.000
                    </span>
                  </div>
                </div>
                <div className="form-section">
                  <span className="section-number">03</span>
                  <h3>
                    Tri thức sử dụng{" "}
                    <span className="count">
                      {config.knowledge_version_ids?.length ?? 0}
                    </span>
                  </h3>
                  <p className="subtle">
                    Chọn đúng phiên bản. Nội dung chưa xác nhận công khai chỉ
                    dùng để xem thử.
                  </p>
                  <KnowledgePicker selected={config.knowledge_version_ids ?? []} onChange={(ids) => update({ knowledge_version_ids: ids })} refreshKey={docs} />
                </div>
                <div className="form-section">
                  <span className="section-number">04</span>
                  <h3>Câu hỏi gợi ý</h3>
                  <label>
                    Mỗi dòng một câu, tối đa 6 câu
                    <textarea
                      rows={3}
                      value={(config.conversation_starters ?? []).join("\n")}
                      onChange={(e) =>
                        update({
                          conversation_starters: e.target.value
                            .split("\n")
                            .slice(0, 6),
                        })
                      }
                    />
                  </label>
                </div>
                <div className="card-actions">
                  <span className="subtle">
                    {dirty
                      ? "Bạn có thay đổi chưa lưu"
                      : "Bản nháp đã được lưu"}
                  </span>
                  <button
                    className="button primary"
                    disabled={busy || !dirty}
                    onClick={save}
                  >
                    Lưu nháp
                  </button>
                </div>
              </section>
              <aside className="preview-column">
                <div className="preview-heading">
                  <div>
                    <span className="eyebrow">PLAYGROUND</span>
                    <h2>Xem thử trợ lý</h2>
                  </div>
                  <span className="badge neutral">Nội bộ</span>
                </div>
                {dirty && (
                  <div className="notice">
                    Hãy lưu nháp để Preview sử dụng thay đổi mới.
                  </div>
                )}
                <Chat
                  preview
                  testing={view.testing}
                  csrf={profile.csrf_token}
                  name={view.config.name}
                  welcome={view.config.welcome_message}
                  revision={view.revision}
                />
                <div className="preview-hint">
                  <strong>Kiểm tra trước khi xuất bản</strong>
                  <p>
                    Đặt câu hỏi thực tế, mở nguồn và xem trợ lý có trả lời đúng
                    phạm vi hay không.
                  </p>
                </div>
              </aside>
            </div>
          )}
          {nav === "knowledge" && (
            <div className="knowledge-grid">
              <KnowledgeFiles
                docs={docs}
                csrf={profile.csrf_token}
                onRefresh={refreshDocs}
              />
              <form className="card text-editor" onSubmit={addText}>
                <div className="card-heading">
                  <div>
                    <h2>Soạn tri thức mới</h2>
                    <p>Nội dung được lưu nháp, chưa công khai.</p>
                  </div>
                </div>
                <label>
                  Tiêu đề tài liệu
                  <input
                    required
                    maxLength={200}
                    value={textTitle}
                    onChange={(e) => setTextTitle(e.target.value)}
                    placeholder="Ví dụ: Hướng dẫn tiếp nhận thông tin"
                  />
                </label>
                <label>
                  Nội dung văn bản
                  <textarea
                    required
                    maxLength={100000}
                    rows={14}
                    value={textBody}
                    onChange={(e) => setTextBody(e.target.value)}
                    placeholder="Nhập nội dung đã được kiểm tra. Có thể dùng Markdown; HTML không được thực thi."
                  />
                </label>
                <div className="notice">
                  Văn bản được lập chỉ mục ngay; cần xác nhận công khai trước
                  khi xuất bản.
                </div>
                <button
                  className="button primary"
                  disabled={busy}
                  type="submit"
                >
                  Lưu văn bản
                </button>
              </form>
            </div>
          )}
          {nav === "releases" && (
            <div className="release-grid">
              <section className="card publish-card">
                <span className="eyebrow">TỪ BẢN NHÁP ĐẾN NGƯỜI DÂN</span>
                <h2>Kiểm tra rồi xuất bản</h2>
                <p className="subtle">
                  Bản xuất bản là ảnh chụp nội dung không thể sửa. Tài liệu cần
                  được xác nhận công khai và còn hiệu lực.
                </p>
                {dirty && (
                  <div className="notice">
                    Có thay đổi chưa lưu. Quay lại cấu hình và lưu nháp trước.
                  </div>
                )}
                <button
                  className="button secondary"
                  disabled={busy || dirty}
                  onClick={() =>
                    perform(async () => {
                      const r = await api<{
                        validation_id: string;
                        checks: string[];
                      }>(
                        "/admin/releases/validate",
                        {
                          method: "POST",
                          headers: { "If-Match": `"${view.revision}"` },
                        },
                        profile.csrf_token,
                      );
                      setPreflight(r);
                      setNotice(
                        "Kiểm tra điều kiện xuất bản đạt. Cần đánh giá nghiệp vụ và chất lượng câu trả lời trước khi đưa vào sử dụng.",
                      );
                    })
                  }
                >
                  ✓ Kiểm tra bản nháp #{view.revision}
                </button>
                {preflight && (
                  <div className="check-list">
                    {preflight.checks.map((c) => (
                      <div key={c}>
                        <span>✓</span>
                        {c}
                      </div>
                    ))}
                  </div>
                )}
                <label>
                  Lý do xuất bản
                  <textarea
                    rows={3}
                    value={reason}
                    minLength={3}
                    maxLength={500}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Nêu ngắn gọn nội dung thay đổi…"
                  />
                </label>
                <button
                  className="button primary"
                  disabled={
                    busy || dirty || !preflight || reason.trim().length < 3
                  }
                  onClick={() =>
                    perform(async () => {
                      await api(
                        "/admin/releases",
                        {
                          method: "POST",
                          headers: { "If-Match": `"${view.revision}"` },
                          body: JSON.stringify({
                            validation_id: preflight!.validation_id,
                            reason,
                          }),
                        },
                        profile.csrf_token,
                      );
                      await load();
                      setReason("");
                      setNotice(
                        "Đã xuất bản. Lượt hỏi mới sử dụng nội dung vừa công bố.",
                      );
                    })
                  }
                >
                  Xuất bản nội dung ↑
                </button>
              </section>
              <section className="card">
                <div className="card-heading">
                  <div>
                    <h2>Lịch sử phiên bản</h2>
                    <p>
                      Khôi phục vẫn kiểm tra quyền và tình trạng thu hồi hiện
                      tại.
                    </p>
                  </div>
                </div>
                {releases.map((r) => (
                  <article key={r.id} className="release-row">
                    <div className="release-dot" />
                    <div>
                      <strong>
                        Phiên bản {r.sequence}{" "}
                        {r.id === view.active_release_id && (
                          <span className="badge teal">Đang hoạt động</span>
                        )}
                      </strong>
                      <p>{r.reason}</p>
                      <small>{localDate(r.created_at)}</small>
                    </div>
                    {r.id !== view.active_release_id && (
                      <button
                        className="button secondary small"
                        disabled={busy}
                        onClick={() => {
                          const note = window.prompt(
                            "Lý do khôi phục nội dung (ít nhất 3 ký tự):",
                          );
                          if (note)
                            perform(async () => {
                              await api(
                                `/admin/releases/${r.id}/rollback`,
                                {
                                  method: "POST",
                                  body: JSON.stringify({ reason: note }),
                                },
                                profile.csrf_token,
                              );
                              await load();
                              setNotice(
                                "Đã khôi phục bằng một bản xuất bản mới.",
                              );
                            });
                        }}
                      >
                        Khôi phục
                      </button>
                    )}
                  </article>
                ))}
                {!releases.length && (
                  <div className="empty-state">Chưa có bản xuất bản.</div>
                )}
              </section>
            </div>
          )}
          {nav === "overview" && (
            <>
              <div className="stat-grid">
                <div className="card stat">
                  <span>VĂN BẢN TRI THỨC</span>
                  <strong>{dashboard?.documents.n ?? "—"}</strong>
                  <small>Nội dung của phường</small>
                </div>
                <div className="card stat">
                  <span>LƯỢT HỎI</span>
                  <strong>{dashboard?.turns.n ?? "—"}</strong>
                  <small>Bao gồm lượt xem thử</small>
                </div>
                <div className="card stat">
                  <span>PHIÊN BẢN ĐANG HOẠT ĐỘNG</span>
                  <strong>
                    {releases.find((r) => r.id === view.active_release_id)
                      ?.sequence ?? "—"}
                  </strong>
                  <small>
                    {dashboard?.paused ? "Đang tạm dừng" : "Tiếp nhận câu hỏi"}
                  </small>
                </div>
              </div>
              <section className="card overview-card">
                <h2>Kiểm soát nội dung đang phục vụ</h2>
                <p>
                  Tạm dừng để rà soát nội dung. Việc dừng có hiệu lực với lượt
                  trả lời chưa phát hành.
                </p>
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() =>
                    perform(async () => {
                      const r = await api<{ paused: boolean }>(
                        "/admin/assistant/pause",
                        { method: "POST" },
                        profile.csrf_token,
                      );
                      setDashboard((d) => (d ? { ...d, paused: r.paused } : d));
                      setNotice(
                        r.paused
                          ? "Đã tạm dừng trợ lý."
                          : "Đã tiếp tục trợ lý.",
                      );
                    })
                  }
                >
                  {dashboard?.paused ? "Tiếp tục trợ lý" : "Tạm dừng trợ lý"}
                </button>
                <h3>Mã nhúng cùng nguồn</h3>
                <textarea
                  readOnly
                  rows={3}
                  value={`<iframe src="${window.location.origin}/embed/${view.public_key}" title="Trợ lý thông tin phường" width="420" height="680"></iframe>`}
                />
                <small>
                  Nhúng trên website khác cần Developer xác nhận domain và cấu
                  hình CSP.
                </small>
              </section>
              <section className="card">
                <div className="card-heading">
                  <div>
                    <h2>Nhật ký hoạt động</h2>
                    <p>Thao tác trong phạm vi đơn vị.</p>
                  </div>
                </div>
                {auditItems.map((a, i) => (
                  <div className="audit-row" key={i}>
                    <span>◷</span>
                    <strong>{a.event_type}</strong>
                    <small>{localDate(a.created_at)}</small>
                  </div>
                ))}
              </section>
            </>
          )}
        </main>
        <footer className="workspace-footer">
          Nội dung thuộc phạm vi đơn vị · Bản phát triển
        </footer>
      </div>
    </div>
  );
}
