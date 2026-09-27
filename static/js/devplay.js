/* DevPlay Flask — interacciones vanilla JS (mismo espíritu que la original) */

// ═══ Utilidades ═══
function escapeHtml(s) {
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}
function toast(msg, type) {
  const box = document.getElementById('toasts');
  const t = document.createElement('div');
  t.className = 'toast-retro';
  t.dataset.type = type || 'info';
  t.textContent = msg;
  box.appendChild(t);
  setTimeout(() => { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(() => t.remove(), 320); }, 3600);
}

// ═══ Tema ═══
function toggleTheme() {
  const dark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('theme', dark ? 'dark' : 'light');
  const b = document.getElementById('themeBtn');
  if (b) b.textContent = dark ? '☀️' : '🌙';
}
(function () {
  const b = document.getElementById('themeBtn');
  if (b) b.textContent = document.documentElement.classList.contains('dark') ? '☀️' : '🌙';
})();

// ═══ Menú usuario ═══
function toggleMenu(e) {
  e.stopPropagation();
  document.getElementById('userMenu').classList.toggle('open');
}
document.addEventListener('click', () => {
  const m = document.getElementById('userMenu');
  if (m) m.classList.remove('open');
});

// ═══ Lightbox ═══
function openLightbox(src) {
  const lb = document.getElementById('lightbox');
  const c = document.getElementById('lbContent');
  if (/\.(mp4|webm|mov)(\?|#|$)/i.test(src)) c.innerHTML = `<video src="${src}" controls autoplay></video>`;
  else c.innerHTML = `<img src="${src}" alt="">`;
  lb.classList.add('open');
}
function closeLightbox(e) {
  if (e.target.id === 'lightbox' || e.target.classList.contains('lb-x')) {
    document.getElementById('lightbox').classList.remove('open');
    document.getElementById('lbContent').innerHTML = '';
  }
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('lightbox').classList.remove('open');
    document.getElementById('lbContent').innerHTML = '';
  }
});

// ═══ Likes y comentarios ═══
async function toggleLike(btn, postId) {
  const r = await fetch(`/api/post/${postId}/like`, { method: 'POST' });
  if (!r.ok) return toast((await r.json()).error || 'Error', 'error');
  const d = await r.json();
  btn.querySelector('.ic').textContent = d.liked ? '♥' : '♡';
  btn.querySelector('.cnt').textContent = d.count;
  btn.classList.toggle('on', d.liked);
  const ic = btn.querySelector('.ic');
  ic.classList.remove('like-pop'); void ic.offsetWidth; ic.classList.add('like-pop');
}
async function sendComment(postId) {
  const input = document.getElementById('commentInput');
  if (!input || !input.value.trim()) return;
  const r = await fetch(`/api/post/${postId}/comment`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: input.value.trim() })
  });
  const d = await r.json();
  if (!r.ok) return toast(d.error || 'Error', 'error');
  const list = document.getElementById('commentList');
  list.insertAdjacentHTML('beforeend', `
    <div class="comment-item">
      <img class="avatar av-sm" src="${d.avatar}">
      <div class="comment-bubble"><b style="font-size:.78rem;">@${escapeHtml(d.username)}</b><div>${escapeHtml(d.content)}</div></div>
    </div>`);
  input.value = '';
}
function focusComments(postId) {
  const zone = document.getElementById('cz-' + postId);
  if (!zone) return;
  zone.style.display = zone.style.display === 'none' ? 'block' : 'none';
  if (zone.style.display === 'block' && !zone.dataset.loaded) {
    zone.dataset.loaded = '1';
    zone.innerHTML = `<div class="comment-box"><input class="input" placeholder="Escribe tu comentario..." maxlength="1000"><button class="btn btn-primary btn-sm btn-press" onclick="sendFeedComment('${postId}', this)">Enviar</button></div>`;
  }
}
async function sendFeedComment(postId, btn) {
  const input = btn.parentElement.querySelector('input');
  if (!input.value.trim()) return;
  const r = await fetch(`/api/post/${postId}/comment`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: input.value.trim() })
  });
  const d = await r.json();
  if (!r.ok) return toast(d.error || 'Error', 'error');
  btn.parentElement.insertAdjacentHTML('afterend', `
    <div class="comment-item">
      <img class="avatar av-sm" src="${d.avatar}">
      <div class="comment-bubble"><b style="font-size:.78rem;">@${escapeHtml(d.username)}</b><div>${escapeHtml(d.content)}</div></div>
    </div>`);
  input.value = '';
}

// ═══ Seguir ═══
async function toggleFollow(btn, username) {
  const r = await fetch(`/api/seguir/${username}`, { method: 'POST' });
  const d = await r.json();
  if (!r.ok) return toast(d.error || 'Error', 'error');
  const on = d.following;
  btn.dataset.following = on ? '1' : '0';
  btn.textContent = on ? 'Siguiendo ✓' : '＋ Seguir';
  btn.classList.toggle('btn-ghost', on);
  btn.classList.toggle('btn-primary', !on);
  toast(on ? `¡Ahora sigues a @${username}! ✨` : `Dejaste de seguir a @${username}`, 'success');
  // Actualiza contador si existe
  const stat = document.querySelector('.stat b');
  // no-op simple; los contadores se refrescan al recargar
}

// ═══ Composer del feed ═══
const postMediaUrls = [];
async function uploadPostMedia(files) {
  for (const f of files) {
    if (postMediaUrls.length >= 5) { toast('Máximo 5 archivos por post', 'warning'); break; }
    const fd = new FormData(); fd.append('file', f); fd.append('kind', 'media');
    const r = await fetch('/api/upload', { method: 'POST', body: fd });
    const d = await r.json();
    if (!r.ok) { toast(d.error || 'No se pudo subir', 'error'); continue; }
    postMediaUrls.push(d);
    renderPostMedia();
  }
  document.getElementById('postFile').value = '';
}
function renderPostMedia() {
  const strip = document.getElementById('postMedia');
  strip.innerHTML = postMediaUrls.map((m, i) => {
    const isVid = m.mediaKind === 'video';
    const inner = isVid ? `<video src="${m.url}" muted loop playsinline></video>` : `<img src="${m.url}">`;
    const badge = isVid ? '<span class="mbadge">▶ video</span>' : (m.url.endsWith('.gif') ? '<span class="mbadge">gif</span>' : '');
    return `<div class="media-thumb">${inner}${badge}<button type="button" class="mx" onclick="delPostMedia(${i})">✕</button></div>`;
  }).join('');
  document.getElementById('postMediaCount').textContent = postMediaUrls.length + '/5';
}
function delPostMedia(i) { postMediaUrls.splice(i, 1); renderPostMedia(); }
async function createPost() {
  const text = document.getElementById('postText').value.trim();
  if (!text && !postMediaUrls.length) return toast('Escribe algo o sube una imagen jaja', 'warning');
  const r = await fetch('/api/post', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: text, media: postMediaUrls.map(m => ({ url: m.url, kind: m.mediaKind })) })
  });
  const d = await r.json();
  if (!r.ok) return toast(d.error || 'Error', 'error');
  toast('¡Publicado en la gaceta! ✍️', 'success');
  setTimeout(() => location.reload(), 700);
}

// ═══ Pixel, el asistente ═══
function togglePixel() {
  const panel = document.getElementById('pixelPanel');
  panel.classList.toggle('open');
  if (panel.classList.contains('open')) {
    document.getElementById('pixelInput').focus();
    scrollPixel();
  }
}
function scrollPixel() {
  const s = document.getElementById('pixelScroll');
  s.scrollTop = s.scrollHeight;
}
async function sendPixel() {
  const inp = document.getElementById('pixelInput');
  const msg = inp.value.trim();
  if (!msg) return;
  inp.value = '';
  const s = document.getElementById('pixelScroll');
  s.insertAdjacentHTML('beforeend', `<div class="pixel-msg user">${escapeHtml(msg)}</div>`);
  s.insertAdjacentHTML('beforeend', `<div class="pixel-msg bot" id="pixelTyping"><span class="typing-dot"></span> <span class="typing-dot"></span> <span class="typing-dot"></span></div>`);
  scrollPixel();
  const r = await fetch('/api/pixel', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg })
  });
  const d = await r.json();
  document.getElementById('pixelTyping')?.remove();
  if (!r.ok) {
    s.insertAdjacentHTML('beforeend', `<div class="pixel-msg bot">${escapeHtml(d.error || 'Ay, me trabé jaja. Intenta de nuevo.')}</div>`);
  } else {
    s.insertAdjacentHTML('beforeend', `<div class="pixel-msg bot">${escapeHtml(d.reply)}</div>`);
  }
  scrollPixel();
}
document.addEventListener('DOMContentLoaded', () => {
  const pi = document.getElementById('pixelInput');
  if (pi) pi.addEventListener('keydown', e => { if (e.key === 'Enter') sendPixel(); });
});
