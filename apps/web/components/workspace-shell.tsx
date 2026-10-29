"use client";

import {
  Activity,
  ArrowUp,
  BookOpen,
  Bot,
  ChevronDown,
  Clock3,
  FileText,
  FolderKanban,
  Grid2X2,
  Link2,
  MemoryStick,
  MessageSquareText,
  MoreHorizontal,
  PanelRight,
  Plus,
  Search,
  Settings,
  Sparkles,
  Upload,
  UserRound,
} from "lucide-react";
import { type FormEvent, useRef, useState } from "react";

type InspectorTab = "Sources" | "Memory" | "Activity";
type WorkspaceMode = "Overview" | "Research" | "Reports";

interface ChatMessage {
  id: number;
  role: "assistant" | "user";
  content: string;
}

const initialMessages: ChatMessage[] = [
  {
    id: 1,
    role: "assistant",
    content: "The launch brief and architecture notes are ready. What should we examine?",
  },
];

const sourceRows = [
  { name: "Launch brief.pdf", detail: "24 pages", status: "Indexed" },
  { name: "Architecture notes.md", detail: "Updated today", status: "Indexed" },
  { name: "Customer calls", detail: "12 transcripts", status: "Syncing" },
];

export function WorkspaceShell() {
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("Sources");
  const [mode, setMode] = useState<WorkspaceMode>("Overview");
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [uploadedFile, setUploadedFile] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) return;

    setMessages((current) => [
      ...current,
      { id: Date.now(), role: "user", content },
      {
        id: Date.now() + 1,
        role: "assistant",
        content: "This workspace is ready for the knowledge-chat API connection.",
      },
    ]);
    setDraft("");
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup" aria-label="Mosaic home">
          <span className="brand-mark"><Grid2X2 size={17} strokeWidth={2.4} /></span>
          <span className="brand-name">Mosaic</span>
        </div>

        <button className="project-switcher" type="button">
          <FolderKanban size={16} />
          <span>Product launch</span>
          <ChevronDown size={14} />
        </button>

        <div className="topbar-actions">
          <button className="icon-button" type="button" aria-label="Search" title="Search">
            <Search size={18} />
          </button>
          <button className="icon-button" type="button" aria-label="Settings" title="Settings">
            <Settings size={18} />
          </button>
          <button className="avatar-button" type="button" aria-label="Account">SC</button>
        </div>
      </header>

      <div className="workspace-grid">
        <aside className="chat-panel" aria-label="Chat and control">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Conversation</span>
              <h1>Launch research</h1>
            </div>
            <button
              className="icon-button"
              type="button"
              aria-label="New conversation"
              title="New conversation"
            >
              <Plus size={18} />
            </button>
          </div>

          <div className="message-list" aria-live="polite">
            {messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <span className="message-avatar" aria-hidden="true">
                  {message.role === "assistant" ? <Bot size={16} /> : <UserRound size={16} />}
                </span>
                <p>{message.content}</p>
              </article>
            ))}
          </div>

          <form className="composer" onSubmit={submitMessage}>
            <label className="sr-only" htmlFor="chat-input">Message Mosaic</label>
            <textarea
              id="chat-input"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask about this project"
              rows={3}
            />
            <div className="composer-footer">
              <button
                className="icon-button subtle"
                type="button"
                aria-label="Attach source"
                title="Attach source"
              >
                <Link2 size={17} />
              </button>
              <button
                className="send-button"
                type="submit"
                aria-label="Send message"
                disabled={!draft.trim()}
              >
                <ArrowUp size={17} />
              </button>
            </div>
          </form>
        </aside>

        <section className="main-workspace" aria-label="Knowledge workspace">
          <div className="workspace-toolbar">
            <div className="segmented-control" aria-label="Workspace mode">
              {(["Overview", "Research", "Reports"] as WorkspaceMode[]).map((item) => (
                <button
                  className={mode === item ? "active" : ""}
                  key={item}
                  type="button"
                  onClick={() => setMode(item)}
                >
                  {item}
                </button>
              ))}
            </div>
            <div className="toolbar-actions">
              <span className="sync-status"><span /> Synced</span>
              <button
                className="icon-button"
                type="button"
                aria-label="More options"
                title="More options"
              >
                <MoreHorizontal size={19} />
              </button>
            </div>
          </div>

          <div className="workspace-content">
            <div className="content-title-row">
              <div>
                <span className="eyebrow">Project knowledge</span>
                <h2>{mode}</h2>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                hidden
                onChange={(event) => setUploadedFile(event.target.files?.[0]?.name ?? null)}
              />
              <button
                className="primary-button"
                type="button"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload size={16} /> Upload
              </button>
            </div>

            {uploadedFile && (
              <div className="upload-notice" role="status">
                <FileText size={17} />
                <span>{uploadedFile}</span>
                <strong>Ready to ingest</strong>
              </div>
            )}

            <section className="metric-strip" aria-label="Project summary">
              <div><strong>15</strong><span>Sources</span></div>
              <div><strong>128</strong><span>Evidence items</span></div>
              <div><strong>9</strong><span>Memories</span></div>
              <div><strong>3</strong><span>Open questions</span></div>
            </section>

            <section className="knowledge-section">
              <div className="section-heading">
                <div>
                  <h3>Knowledge map</h3>
                  <p>Topics with the strongest source coverage</p>
                </div>
                <button className="text-button" type="button">View graph</button>
              </div>
              <div className="topic-grid">
                <article className="topic-card accent-green">
                  <span className="topic-icon"><BookOpen size={18} /></span>
                  <div><h4>Market landscape</h4><p>6 sources · 42 evidence items</p></div>
                  <span className="coverage">Strong</span>
                </article>
                <article className="topic-card accent-blue">
                  <span className="topic-icon"><MessageSquareText size={18} /></span>
                  <div><h4>Customer needs</h4><p>12 calls · 51 evidence items</p></div>
                  <span className="coverage">Strong</span>
                </article>
                <article className="topic-card accent-amber">
                  <span className="topic-icon"><Sparkles size={18} /></span>
                  <div><h4>Launch positioning</h4><p>3 sources · 18 evidence items</p></div>
                  <span className="coverage">Growing</span>
                </article>
              </div>
            </section>

            <section className="knowledge-section recent-section">
              <div className="section-heading">
                <div><h3>Recent work</h3><p>Latest project changes and agent activity</p></div>
              </div>
              <div className="activity-table">
                <div className="activity-row">
                  <span className="activity-icon"><FileText size={17} /></span>
                  <div><strong>Architecture notes indexed</strong><span>14 evidence items added</span></div>
                  <time>8 min</time>
                </div>
                <div className="activity-row">
                  <span className="activity-icon"><Bot size={17} /></span>
                  <div><strong>Research summary completed</strong><span>Market landscape</span></div>
                  <time>32 min</time>
                </div>
              </div>
            </section>
          </div>
        </section>

        <aside className="inspector-panel" aria-label="Project inspector">
          <div className="inspector-tabs" role="tablist">
            {(["Sources", "Memory", "Activity"] as InspectorTab[]).map((tab) => (
              <button
                aria-selected={inspectorTab === tab}
                className={inspectorTab === tab ? "active" : ""}
                key={tab}
                onClick={() => setInspectorTab(tab)}
                role="tab"
                type="button"
              >
                {tab}
              </button>
            ))}
          </div>

          <div className="inspector-content">
            {inspectorTab === "Sources" && (
              <>
                <div className="inspector-heading">
                  <div><h2>Sources</h2><span>15 total</span></div>
                  <button
                    className="icon-button"
                    type="button"
                    aria-label="Add source"
                    title="Add source"
                  >
                    <Plus size={18} />
                  </button>
                </div>
                <div className="source-list">
                  {sourceRows.map((source) => (
                    <article className="source-card" key={source.name}>
                      <span className="file-tile"><FileText size={17} /></span>
                      <div><h3>{source.name}</h3><p>{source.detail}</p></div>
                      <span className={`source-status ${source.status.toLowerCase()}`}>
                        {source.status}
                      </span>
                    </article>
                  ))}
                </div>
              </>
            )}
            {inspectorTab === "Memory" && (
              <div className="empty-panel">
                <MemoryStick size={22} />
                <h2>Project memory</h2>
                <p>9 accepted memories</p>
                <button className="secondary-button" type="button">Review memories</button>
              </div>
            )}
            {inspectorTab === "Activity" && (
              <div className="empty-panel">
                <Activity size={22} />
                <h2>Agent activity</h2>
                <p>All tasks are complete</p>
                <button className="secondary-button" type="button">Open timeline</button>
              </div>
            )}
          </div>

          <footer className="inspector-footer">
            <Clock3 size={15} /> Last indexed 8 minutes ago
            <PanelRight size={16} />
          </footer>
        </aside>
      </div>
    </main>
  );
}
