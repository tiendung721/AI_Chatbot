"use client";
import { FormEvent, useEffect, useRef, useState } from "react";
import { api, type SessionView, type TurnView } from "@/lib/api";
import { locationLabel, type Locator } from "@/lib/locator";

type Props = {
  publicKey?: string;
  preview?: boolean;
  testing?: boolean;
  csrf?: string;
  name?: string;
  welcome?: string;
  revision?: number;
};
type Message = {
  id: string;
  question: string;
  result?: TurnView;
  error?: string;
};
type PublicInfo = {
  name: string;
  welcome_message: string;
  tenant_name: string;
  published: boolean;
  paused: boolean;
  testing: boolean;
  conversation_starters: string[];
};
export default function Chat({
  publicKey,
  preview = false,
  testing,
  csrf,
  name,
  welcome,
  revision,
}: Props) {
  const [info, setInfo] = useState<PublicInfo | null>(null);
  const [session, setSession] = useState<SessionView | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [source, setSource] = useState<{
    title: string;
    body: string;
    section: number;
    locator?: Locator | null;
  } | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const abort = useRef<AbortController | null>(null);
  const modal = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!source) return;
    const previous = document.activeElement as HTMLElement | null;
    modal.current?.querySelector<HTMLButtonElement>("button")?.focus();
    function keydown(event: KeyboardEvent) {
      if (event.key === "Escape") setSource(null);
      if (event.key === "Tab") {
        event.preventDefault();
        modal.current?.querySelector<HTMLButtonElement>("button")?.focus();
      }
    }
    document.addEventListener("keydown", keydown);
    return () => {
      document.removeEventListener("keydown", keydown);
      previous?.focus();
    };
  }, [source]);
  useEffect(() => {
    if (publicKey)
      api<PublicInfo>(`/public/assistants/${encodeURIComponent(publicKey)}`)
        .then(setInfo)
        .catch((e) => setError(String(e.message)));
  }, [publicKey]);
  useEffect(() => {
    abort.current?.abort();
    setSession(null);
    setMessages([]);
    setBusy(false);
    setError("");
  }, [revision]);
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => {
    scroller.current?.scrollTo({
      top: scroller.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, status]);
  async function send(event: FormEvent) {
    event.preventDefault();
    const question = input.trim();
    if (!question || busy) return;
    const id = crypto.randomUUID();
    setInput("");
    setBusy(true);
    setError("");
    setMessages((m) => [...m, { id, question }]);
    setStatus("Đang tiếp nhận câu hỏi…");
    let turnId: string | undefined;
    let active = session;
    try {
      if (!active) {
        active = await api<SessionView>(
          preview
            ? "/admin/assistant/preview/sessions"
            : `/public/assistants/${encodeURIComponent(publicKey ?? "")}/sessions`,
          { method: "POST" },
          csrf,
        );
        setSession(active);
      }
      const turn = await api<{ turn_id: string; events_path: string }>(
        `/chat/sessions/${active.session_id}/turns`,
        {
          method: "POST",
          body: JSON.stringify({
            client_request_id: id,
            message: question,
            attachment_ids: [],
          }),
        },
        undefined,
        active.session_token,
      );
      turnId = turn.turn_id;
      abort.current = new AbortController();
      try {
        const response = await fetch(turn.events_path, {
          headers: { Authorization: `Bearer ${active.session_token}` },
          signal: abort.current.signal,
        });
        if (!response.ok || !response.body)
          throw new Error("Stream chưa kết nối.");
        const reader = response.body.getReader(),
          decoder = new TextDecoder();
        let buffer = "";
        while (true) {
          const part = await reader.read();
          if (part.done) break;
          buffer += decoder.decode(part.value, { stream: true });
          let boundary: number;
          while ((boundary = buffer.indexOf("\n\n")) >= 0) {
            const frame = buffer.slice(0, boundary);
            buffer = buffer.slice(boundary + 2);
            const data = frame.split("\n").find((l) => l.startsWith("data: "));
            if (!data) continue;
            const packet = JSON.parse(data.slice(6)) as {
              payload: { status?: string };
            };
            if (packet.payload.status)
              setStatus(
                (
                  {
                    searching: "Đang tìm trong tri thức…",
                    generating: "Đang chuẩn bị câu trả lời…",
                    validating: "Đang kiểm tra nguồn…",
                  } as Record<string, string>
                )[packet.payload.status] ?? "Đang xử lý…",
              );
          }
        }
      } catch (streamError) {
        if (abort.current?.signal.aborted) throw streamError;
        setStatus("Đang lấy lại kết quả đã lưu…");
      }
      let result = await api<TurnView>(
        `/chat/turns/${turn.turn_id}`,
        {},
        undefined,
        active.session_token,
      );
      for (
        let attempt = 0;
        attempt < 120 && ["queued", "generating"].includes(result.state);
        attempt++
      ) {
        await new Promise((r) => setTimeout(r, 1000));
        result = await api<TurnView>(
          `/chat/turns/${turn.turn_id}`,
          {},
          undefined,
          active.session_token,
        );
      }
      if (["queued", "generating"].includes(result.state))
        throw new Error(
          "Lượt hỏi vẫn đang xử lý. Không tự gửi lại câu hỏi để tránh tạo trùng.",
        );
      setMessages((m) =>
        m.map((message) =>
          message.id === id ? { ...message, result } : message,
        ),
      );
    } catch (e) {
      setMessages((m) =>
        m.map((message) =>
          message.id === id
            ? {
                ...message,
                error: e instanceof Error ? e.message : "Chưa thể trả lời.",
              }
            : message,
        ),
      );
      if (turnId && active && abort.current?.signal.aborted)
        await api(
          `/chat/turns/${turnId}/cancel`,
          { method: "POST" },
          undefined,
          active.session_token,
        ).catch(() => undefined);
    } finally {
      setBusy(false);
      setStatus("");
    }
  }
  async function feedback(turnId: string, rating: "helpful" | "unhelpful") {
    if (!session) return;
    try {
      await api(
        `/chat/turns/${turnId}/feedback`,
        { method: "POST", body: JSON.stringify({ rating, comment: "" }) },
        undefined,
        session.session_token,
      );
      setStatus("Đã ghi nhận đánh giá. Cảm ơn bạn.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chưa lưu được đánh giá.");
    }
  }
  return (
    <section
      className={`chat-panel ${preview ? "preview-panel" : ""}`}
      aria-label={preview ? "Xem thử bản nháp" : "Trò chuyện"}
    >
      <header className="chat-header">
        <div className="avatar">P</div>
        <div>
          <strong>{name ?? info?.name ?? "Trợ lý thông tin"}</strong>
          <div className="subtle">
            <span className="online-dot" />
            {preview
              ? "Xem thử · Bản nháp đã lưu"
              : (info?.tenant_name ?? "Đang kết nối")}
          </div>
        </div>
        {preview && <span className="badge amber">Bản nháp</span>}
      </header>
      {(testing ?? info?.testing) && (
        <div className="test-banner">
          MÔI TRƯỜNG THỬ NGHIỆM — CHƯA KẾT NỐI AI THẬT
        </div>
      )}
      <div className="chat-scroll" ref={scroller}>
        <div className="assistant-message">
          <span className="eyebrow">SẴN SÀNG HỖ TRỢ</span>
          <p>
            {welcome ??
              info?.welcome_message ??
              "Xin chào, bạn cần hỗ trợ nội dung gì?"}
          </p>
          <small>
            Câu trả lời kèm nguồn từ tri thức{" "}
            {preview ? "bản nháp" : "đã xuất bản"}.
          </small>
        </div>
        {!messages.length && (
          <div className="starters">
            {(info?.conversation_starters.length
              ? info.conversation_starters
              : ["Thủ tục minh họa cần chuẩn bị gì?"]
            ).map((s) => (
              <button key={s} className="starter" onClick={() => setInput(s)}>
                {s}
                <span>↗</span>
              </button>
            ))}
          </div>
        )}
        {messages.map((message) => (
          <div key={message.id} className="exchange">
            <div className="user-message">{message.question}</div>
            {message.error && (
              <div role="alert" className="notice error">
                {message.error}
              </div>
            )}
            {message.result && (
              <div className="assistant-message">
                {message.result.state === "failed" ? (
                  <p>
                    Lượt trả lời chưa hoàn tất ({message.result.error_code}).
                    Bạn có thể đặt câu hỏi mới.
                  </p>
                ) : message.result.state === "cancelled" ? (
                  <p>Đã dừng lượt trả lời.</p>
                ) : (
                  <>
                    {message.result.answer?.blocks.map((b, i) => (
                      <p key={i} className="answer-text">
                        {b.text}
                      </p>
                    ))}
                    {message.result.answer?.follow_up_question && (
                      <p>{message.result.answer.follow_up_question}</p>
                    )}
                    {!!message.result.citations.length && (
                      <div className="source-list">
                        <small>NGUỒN THAM KHẢO</small>
                        {message.result.citations.map((c) => (
                          <button
                            className="source-card"
                            key={c.id}
                            onClick={() => {
                              if (session)
                                api<{
                                  title: string;
                                  body: string;
                                  section: number;
                                  locator?: Locator | null;
                                }>(
                                  `/sources/${c.id}`,
                                  {},
                                  undefined,
                                  session.session_token,
                                )
                                  .then(setSource)
                                  .catch((e) => setError(e.message));
                            }}
                          >
                            <span>▤</span>
                            <div>
                              {c.title}
                              <small>
                                Tài liệu của phường ·{" "}
                                {locationLabel(c.locator, c.section)}
                              </small>
                            </div>
                            <span>↗</span>
                          </button>
                        ))}
                      </div>
                    )}
                    <div className="feedback">
                      <span>Câu trả lời có hữu ích?</span>
                      <button
                        onClick={() =>
                          feedback(message.result!.turn_id, "helpful")
                        }
                      >
                        Hữu ích
                      </button>
                      <button
                        onClick={() =>
                          feedback(message.result!.turn_id, "unhelpful")
                        }
                      >
                        Chưa hữu ích
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
        {(status || busy) && (
          <div className="chat-status" role="status">
            {busy && <span className="spinner" />}
            {status}
          </div>
        )}
      </div>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {!preview && (
        <div className="personal-note">
          Tra cứu hồ sơ cá nhân: đơn vị chưa cấu hình đăng nhập và kết nối
          nghiệp vụ.
        </div>
      )}
      <form className="chat-composer" onSubmit={send}>
        <label
          className="sr-only"
          htmlFor={preview ? "preview-question" : "question"}
        >
          Câu hỏi
        </label>
        <textarea
          id={preview ? "preview-question" : "question"}
          placeholder="Nhập câu hỏi của bạn…"
          rows={2}
          maxLength={4000}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={busy}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <button
          className="send-button"
          type="submit"
          disabled={busy || !input.trim()}
          aria-label="Gửi câu hỏi"
        >
          ↑
        </button>
      </form>
      <footer className="chat-footer">
        Kiểm tra nguồn trước khi sử dụng thông tin. Không nhập dữ liệu cá nhân
        vào bản thử nghiệm.
      </footer>
      {source && (
        <div className="modal-backdrop" onClick={() => setSource(null)}>
          <section
            ref={modal}
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Nội dung nguồn"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="close-button"
              onClick={() => setSource(null)}
              aria-label="Đóng nguồn"
            >
              ×
            </button>
            <span className="eyebrow">
              TÀI LIỆU CỦA PHƯỜNG ·{" "}
              {locationLabel(source.locator, source.section)}
            </span>
            <h2>{source.title}</h2>
            <p className="answer-text">{source.body}</p>
          </section>
        </div>
      )}
    </section>
  );
}
