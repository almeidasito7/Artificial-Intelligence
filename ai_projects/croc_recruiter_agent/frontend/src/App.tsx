import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import './App.css'
import { healthCheck, queryAgent } from './api'
import crocProfile from './assets/croc_profile.png'

function App() {
  const BOT_NAME = 'Croc'
  const DEFAULT_USER_ID = 'carol.chen'
  const makeId = () =>
    typeof globalThis.crypto?.randomUUID === 'function'
      ? globalThis.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`

  type ChatMessage = {
    id: string
    role: 'user' | 'bot' | 'system'
    text: string
    createdAt: number
  }

  const [backendOnline, setBackendOnline] = useState<boolean>(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const now = Date.now()
    return [
      {
        id: 'system-date',
        role: 'system',
        text: formatDateDivider(now),
        createdAt: now,
      },
      {
        id: 'bot-greeting',
        role: 'bot',
        text: 'Hi! How can I help you today?',
        createdAt: now + 1,
      },
    ]
  })
  const [draft, setDraft] = useState<string>('')
  const [isTyping, setIsTyping] = useState<boolean>(false)
  const [sendError, setSendError] = useState<string | null>(null)

  const bottomRef = useRef<HTMLDivElement | null>(null)

  const lastMessageTime = useMemo(() => {
    const last = messages[messages.length - 1]
    return last ? formatTime(last.createdAt) : ''
  }, [messages])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        await healthCheck()
        if (cancelled) return
        setBackendOnline(true)
      } catch {
        if (cancelled) return
        setBackendOnline(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  async function onAsk(e: FormEvent) {
    e.preventDefault()
    const question = draft.trim()
    if (!question) return

    setSendError(null)
    setDraft('')

    const userMsg: ChatMessage = {
      id: `u-${makeId()}`,
      role: 'user',
      text: question,
      createdAt: Date.now(),
    }

    setMessages((prev) => [...prev, userMsg])
    setIsTyping(true)

    try {
      const res = await queryAgent({ question, user_id: DEFAULT_USER_ID })
      const answerText = (res.answer || '').trim()

      const botMsg: ChatMessage = {
        id: `b-${makeId()}`,
        role: 'bot',
        text: answerText || 'Não consegui gerar uma resposta agora.',
        createdAt: Date.now(),
      }

      setMessages((prev) => [...prev, botMsg])
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setSendError(msg)
      setMessages((prev) => [
        ...prev,
        {
          id: `b-${makeId()}`,
          role: 'bot',
          text: 'I had trouble reaching the backend. Please try again.',
          createdAt: Date.now(),
        },
      ])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="chat-shell">
      <header className="chat-header">
        <button className="chat-back" type="button" aria-label="Voltar">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M15.5 19.5 8 12l7.5-7.5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        <div className="chat-avatar" aria-hidden="true">
          <img src={crocProfile} alt="" />
        </div>

        <div className="chat-title">
          <div className="chat-name">
            {BOT_NAME}
            <span className="verified" aria-label="Verified" title="Verified">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 2.5 14.9 4.2l3.3-.6 1.5 3.1 3 1.7-1 3.4 1 3.4-3 1.7-1.5 3.1-3.3-.6L12 21.5 9.1 19.8l-3.3.6-1.5-3.1-3-1.7 1-3.4-1-3.4 3-1.7 1.5-3.1 3.3.6L12 2.5Z"
                  fill="#1d9bf0"
                />
                <path
                  d="M9.2 12.3 11 14.2 15.4 9.7"
                  fill="none"
                  stroke="#fff"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </span>
          </div>
          <div className="chat-status">
            <span className={backendOnline ? 'status-dot online' : 'status-dot offline'} aria-hidden="true" />
            {backendOnline ? 'Online now' : 'Offline'}
          </div>
        </div>

        <div className="chat-meta" aria-hidden="true">
          {lastMessageTime}
        </div>
      </header>

      <main className="chat-body" role="log" aria-live="polite">
        {messages.map((m) => {
          if (m.role === 'system') {
            return (
              <div key={m.id} className="chat-divider">
                <span>{m.text}</span>
              </div>
            )
          }

          const isUser = m.role === 'user'
          return (
            <div key={m.id} className={isUser ? 'msg-row right' : 'msg-row left'}>
              {!isUser ? (
                <div className="msg-avatar" aria-hidden="true">
                  <img src={crocProfile} alt="" />
                </div>
              ) : null}
              <div className={isUser ? 'msg-bubble user' : 'msg-bubble bot'}>{renderMessage(m.text)}</div>
            </div>
          )
        })}

        {isTyping ? (
          <div className="msg-row left">
            <div className="msg-avatar" aria-hidden="true">
              <img src={crocProfile} alt="" />
            </div>
            <div className="msg-bubble bot typing" aria-label="Typing">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        ) : null}

        {sendError ? <div className="chat-error">{sendError}</div> : null}
        <div ref={bottomRef} />
      </main>

      <form className="chat-input" onSubmit={onAsk}>
        <input
          className="chat-text"
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Mensagem..."
          autoComplete="off"
          disabled={isTyping}
        />
        <button className="chat-send" type="submit" disabled={!draft.trim() || isTyping}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M3 11.5 21 3l-8.5 18-1.7-7.1L3 11.5Z"
              fill="currentColor"
            />
          </svg>
        </button>
      </form>
    </div>
  )
}

export default App

function formatDateDivider(epochMs: number): string {
  const date = new Date(epochMs)
  const day = date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' })
  const time = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }).replace(':', 'h')
  return `${day}, ${time}`
}

function formatTime(epochMs: number): string {
  return new Date(epochMs).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }).replace(':', 'h')
}

function renderMessage(text: string): ReactNode {
  const lines = (text || '').split('\n')
  const blocks: ReactNode[] = []
  let listItems: ReactNode[] = []

  function flushList(key: string) {
    if (!listItems.length) return
    blocks.push(
      <ul key={key} className="msg-list">
        {listItems.map((item, idx) => (
          <li key={`${key}-${idx}`}>{item}</li>
        ))}
      </ul>,
    )
    listItems = []
  }

  lines.forEach((line, i) => {
    const m = /^\s*[-*]\s+(.*)\s*$/.exec(line)
    if (m) {
      listItems.push(renderInline(m[1]))
      return
    }

    flushList(`list-${i}`)

    if (!line.trim()) {
      blocks.push(<div key={`sp-${i}`} className="msg-spacer" />)
      return
    }

    blocks.push(
      <div key={`p-${i}`} className="msg-line">
        {renderInline(line)}
      </div>,
    )
  })

  flushList('list-end')
  return blocks
}

function renderInline(text: string): ReactNode {
  const out: ReactNode[] = []
  const s = text || ''
  let i = 0

  while (i < s.length) {
    const start = s.indexOf('**', i)
    if (start === -1) {
      out.push(s.slice(i))
      break
    }

    const end = s.indexOf('**', start + 2)
    if (end === -1) {
      out.push(s.slice(i))
      break
    }

    if (start > i) out.push(s.slice(i, start))
    const boldText = s.slice(start + 2, end)
    out.push(<strong key={`${start}-${end}`}>{boldText}</strong>)
    i = end + 2
  }

  return out
}
