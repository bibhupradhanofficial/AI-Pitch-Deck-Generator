const qs = (sel, root = document) => root.querySelector(sel)
const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel))

let activeTone = "professional"
let activeAbort = null
let toastTimer = null

function showToast(message, isError = false) {
  const el = qs("#toast")
  if (!el) return
  el.textContent = message
  el.classList.toggle("is-error", isError)
  el.classList.add("is-visible")
  window.clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => el.classList.remove("is-visible"), 2600)
}

function setTone(nextTone) {
  activeTone = nextTone
  qsa(".pill").forEach((b) => b.classList.toggle("is-active", b.dataset.tone === nextTone))
}

function resetResults() {
  qsa(".card-reveal").forEach((el) => {
    el.classList.add("is-hidden")
    el.classList.remove("is-visible")
  })
  qs("#slidesWrap").innerHTML = ""
  qs("#voiceoverText").textContent = ""
  qs("#captionTwitter").textContent = ""
  qs("#captionLinkedIn").textContent = ""
  qs("#captionInstagram").textContent = ""
  qs("#chartsGrid").innerHTML = ""
  qs("#imagesMasonry").innerHTML = ""
  qs("#pptxBtn").setAttribute("href", "#")
  qs("#pptxBtn").setAttribute("aria-disabled", "true")
  qs("#pptxBtn").addEventListener("click", (e) => e.preventDefault(), { once: true })
  qs("#videoWrap").innerHTML = ""
  qs("#confetti").innerHTML = ""
}

function revealCard(cardEl) {
  if (!cardEl) return
  cardEl.classList.remove("is-hidden")
  requestAnimationFrame(() => cardEl.classList.add("is-visible"))
}

function setStreamVisible(isVisible) {
  const stream = qs("#stream")
  stream.classList.toggle("is-hidden", !isVisible)
}

function setStreamStatus(text) {
  const el = qs("#streamStatus")
  el.textContent = text
}

function pushStatusLog(text) {
  const wrap = qs("#statusLog")
  const item = document.createElement("div")
  item.className = "log-item"
  const dot = document.createElement("div")
  dot.className = "log-dot"
  const t = document.createElement("div")
  t.className = "log-text"
  t.textContent = text
  item.append(dot, t)
  wrap.prepend(item)

  const all = qsa(".log-item", wrap)
  for (let i = 8; i < all.length; i++) all[i].remove()
}

function renderSlides(slides) {
  const wrap = qs("#slidesWrap")
  wrap.innerHTML = ""
    ; (slides || []).forEach((s) => {
      const card = document.createElement("div")
      card.className = "mini-slide"
      const title = document.createElement("div")
      title.className = "mini-title"
      title.textContent = s?.title || "Untitled"
      const ul = document.createElement("ul")
      ul.className = "mini-bullets"
        ; (Array.isArray(s?.body) ? s.body : []).slice(0, 7).forEach((b) => {
          const li = document.createElement("li")
          li.textContent = String(b)
          ul.appendChild(li)
        })
      card.append(title, ul)
      wrap.appendChild(card)
    })
}

function setTabs(active) {
  qsa(".tab").forEach((t) => t.classList.toggle("is-active", t.dataset.tab === active))
  qsa(".tab-panel").forEach((p) => p.classList.toggle("is-active", p.dataset.panel === active))
}

async function copyTextFromSelector(selector) {
  const el = qs(selector)
  if (!el) return
  const text = el.textContent || ""
  try {
    await navigator.clipboard.writeText(text)
    showToast("Copied to clipboard")
  } catch {
    showToast("Copy failed", true)
  }
}

function renderImageGrid(urls, gridEl) {
  gridEl.innerHTML = ""
    ; (urls || []).forEach((u) => {
      const card = document.createElement("div")
      card.className = "img-card"
      const img = document.createElement("img")
      img.loading = "lazy"
      img.alt = "Generated image"
      img.src = u
      card.appendChild(img)
      gridEl.appendChild(card)
    })
}

function renderMasonry(urls, masonryEl) {
  masonryEl.innerHTML = ""
    ; (urls || []).forEach((u) => {
      const item = document.createElement("div")
      item.className = "masonry-item"
      const img = document.createElement("img")
      img.loading = "lazy"
      img.alt = "Generated mockup"
      img.src = u
      item.appendChild(img)
      masonryEl.appendChild(item)
    })
}

function burstConfetti() {
  const host = qs("#confetti")
  if (!host) return
  host.innerHTML = ""
  const colors = ["#667eea", "#764ba2", "#ffffff", "rgba(255,255,255,0.75)"]
  const count = 30
  for (let i = 0; i < count; i++) {
    const p = document.createElement("span")
    p.className = "piece"
    const left = 12 + Math.random() * 76
    const dx = (Math.random() * 180 - 90).toFixed(0) + "px"
    const rot = (Math.random() * 360).toFixed(0) + "deg"
    p.style.left = `${left}%`
    p.style.setProperty("--dx", dx)
    p.style.background = colors[Math.floor(Math.random() * colors.length)]
    p.style.transform = `translate(-50%, 0) rotate(${rot})`
    p.style.animationDelay = `${(Math.random() * 120).toFixed(0)}ms`
    host.appendChild(p)
  }
  window.setTimeout(() => (host.innerHTML = ""), 1200)
}

function renderVideo(videoUrlOrNull) {
  const wrap = qs("#videoWrap")
  wrap.innerHTML = ""
  if (videoUrlOrNull) {
    const video = document.createElement("video")
    video.controls = true
    video.src = videoUrlOrNull
    wrap.appendChild(video)
  } else {
    const note = document.createElement("div")
    note.className = "note"
    note.textContent = "Video generation unavailable."
    wrap.appendChild(note)
  }
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function applyEvent(evt) {
  const t = evt?.type
  if (!t) return

  if (t === "status") {
    const msg = evt?.message || "Working…"
    setStreamStatus(msg)
    pushStatusLog(msg)
    return
  }

  if (t === "slides") {
    renderSlides(Array.isArray(evt.data) ? evt.data : [])
    revealCard(qs("#cardSlides"))
    return
  }

  if (t === "voiceover") {
    qs("#voiceoverText").textContent = typeof evt.data === "string" ? evt.data : ""
    revealCard(qs("#cardVoiceover"))
    return
  }

  if (t === "social") {
    const d = evt.data && typeof evt.data === "object" ? evt.data : {}
    qs("#captionTwitter").textContent = typeof d.twitter === "string" ? d.twitter : ""
    qs("#captionLinkedIn").textContent = typeof d.linkedin === "string" ? d.linkedin : ""
    qs("#captionInstagram").textContent = typeof d.instagram === "string" ? d.instagram : ""
    revealCard(qs("#cardSocial"))
    return
  }

  if (t === "charts") {
    const urls = Array.isArray(evt.data) ? evt.data : []
    renderImageGrid(urls, qs("#chartsGrid"))
    revealCard(qs("#cardCharts"))
    return
  }

  if (t === "images") {
    const urls = Array.isArray(evt.data) ? evt.data : []
    renderMasonry(urls, qs("#imagesMasonry"))
    revealCard(qs("#cardImages"))
    return
  }

  if (t === "pptx") {
    const url = typeof evt.data === "string" && evt.data ? evt.data : null
    const btn = qs("#pptxBtn")
    btn.setAttribute("aria-disabled", url ? "false" : "true")
    btn.href = url || "#"
    if (!url) btn.addEventListener("click", (e) => e.preventDefault(), { once: true })
    revealCard(qs("#cardPptx"))
    if (url) burstConfetti()
    return
  }

  if (t === "video") {
    renderVideo(typeof evt.data === "string" ? evt.data : null)
    revealCard(qs("#cardVideo"))
    return
  }

  if (t === "complete") {
    const msg = evt?.message || "Complete"
    setStreamStatus(msg)
    pushStatusLog(msg)
  }
}

async function streamGenerate(payload) {
  if (activeAbort) activeAbort.abort()
  activeAbort = new AbortController()
  const btn = qs("#generateBtn")
  btn.disabled = true

  setStreamVisible(true)
  setStreamStatus("Starting…")
  qs("#statusLog").innerHTML = ""
  resetResults()

  try {
    const res = await fetch("http://localhost:8080/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: activeAbort.signal,
    })

    if (!res.ok) {
      const text = await res.text()
      throw new Error(text || `${res.status} ${res.statusText}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder("utf-8")
    let buffer = ""

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split("\n\n")
      buffer = parts.pop() || ""

      for (const part of parts) {
        const lines = part.split("\n")
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith("data:")) continue
          const jsonText = trimmed.replace(/^data:\s?/, "")
          const evt = safeJsonParse(jsonText)
          if (evt) applyEvent(evt)
        }
      }
    }
  } catch (err) {
    if (err?.name === "AbortError") return
    showToast("Stream failed. Check backend logs.", true)
    setStreamStatus(`Error: ${err?.message || String(err)}`)
    pushStatusLog(`Error: ${err?.message || String(err)}`)
  } finally {
    btn.disabled = false
    activeAbort = null
  }
}

window.addEventListener("DOMContentLoaded", () => {
  setTone(activeTone)
  setTabs("twitter")

  qs("#pitchForm").addEventListener("submit", (e) => {
    e.preventDefault()
    const idea = qs("#idea").value.trim()
    if (!idea) {
      showToast("Please describe your startup idea.", true)
      return
    }
    const payload = {
      idea,
      industry: qs("#industry").value || null,
      target_market: qs("#targetMarket").value || null,
      tone: activeTone,
    }
    streamGenerate(payload)
  })

  qsa(".pill").forEach((b) => {
    b.addEventListener("click", () => setTone(b.dataset.tone))
  })

  qsa(".tab").forEach((t) => {
    t.addEventListener("click", () => setTabs(t.dataset.tab))
  })

  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-copy]")
    if (!btn) return
    const sel = btn.getAttribute("data-copy")
    if (sel) copyTextFromSelector(sel)
  })
})
