/* ==========================================================================
   app.js: utilidades compartidas por todas las páginas

   Sesión
   - access token: solo en memoria (variable Sesion.access). Se pierde al cambiar de página.
   - refresh token: cookie HttpOnly que pone el servidor; JavaScript no puede leerla.
   - En cada página, alIniciar() pide un access nuevo usando esa cookie.
   ========================================================================== */

/* ---- Atajos y formato ---- */
const $ = (selector) => document.querySelector(selector);
const dinero = (n) => '$' + Number(n).toLocaleString('es-CL', { maximumFractionDigits: 0 });
const fecha = (iso) => new Date(iso).toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' });
const TAM = 9; // elementos por página en los listados (se envía como ?page_size=)

// Escapa texto antes de meterlo en innerHTML (evita inyección de HTML/JS)
const esc = (texto) => String(texto ?? '').replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ---- Sesión ---- */
const Sesion = {
  access: null,

  guardar(datos) {
    this.access = datos.access;
    localStorage.setItem('sesion', '1'); // solo una marca ("hay sesión"), no contiene ningún token
  },
  limpiar() {
    this.access = null;
    localStorage.removeItem('sesion');
  },
  // Lee el payload del token (claims). Solo sirve para dibujar la interfaz;
  // la seguridad real la aplica el backend en cada petición.
  claims() {
    if (!this.access) return null;
    try { return JSON.parse(atob(this.access.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))); }
    catch { return null; }
  },
  rol() { const c = this.claims(); return c ? c.rol : null; },

  // Pide un access nuevo. El navegador adjunta solo la cookie HttpOnly del refresh token.
  async renovar() {
    if (!localStorage.getItem('sesion')) return false;
    const r = await fetch('/api/auth/refresh/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    if (r.ok) { this.access = (await r.json()).access; return true; }
    this.limpiar(); // el refresh venció o fue invalidado: no hay sesión
    return false;
  },
};

/* ---- api(): fetch con JWT y renovación automática del access token ---- */
async function api(url, { method = 'GET', body = null } = {}) {
  const pedir = () => {
    const headers = { 'Content-Type': 'application/json' };
    if (Sesion.access) headers.Authorization = 'Bearer ' + Sesion.access;
    return fetch(url, { method, headers, body: body ? JSON.stringify(body) : null });
  };

  let res = await pedir();

  // 401 con token enviado = access expirado: se renueva y se repite la petición una vez
  if (res.status === 401 && Sesion.access) {
    await Sesion.renovar();
    res = await pedir();
  }

  const data = res.status === 204 ? null : await res.json().catch(() => null);
  return { ok: res.ok, status: res.status, data };
}

/* ---- Mensajes de error / aviso ---- */
function errorTexto(data) {
  if (!data) return 'Ocurrió un error inesperado.';
  if (data.detail) return data.detail;
  return Object.entries(data).map(([campo, msg]) => `${campo}: ${[].concat(msg).join(' ')}`).join(' | ');
}

function aviso(html, ok) {
  const caja = $('#msg');
  caja.innerHTML = html;
  caja.className = 'aviso ' + (ok ? 'ok' : 'error');
  caja.hidden = false;
}

/* ---- Paginador: dibuja "Anterior / Página X de Y / Siguiente" ---- */
function paginador(contenedor, total, pagina, alCambiar) {
  const paginas = Math.ceil(total / TAM);
  contenedor.innerHTML = paginas > 1 ? `
    <button class="link" data-pagina="${pagina - 1}" ${pagina <= 1 ? 'disabled' : ''}>Anterior</button>
    <span>Página ${pagina} de ${paginas}</span>
    <button class="link" data-pagina="${pagina + 1}" ${pagina >= paginas ? 'disabled' : ''}>Siguiente</button>` : '';
  contenedor.onclick = (e) => {
    const boton = e.target.closest('[data-pagina]');
    if (boton && !boton.disabled) alCambiar(Number(boton.dataset.pagina));
  };
}

/* ---- Inicio de página: espera a conocer la sesión y luego ejecuta el código de la página ---- */
function alIniciar(fn) { Sesion.lista.then(fn); }

// Devuelve false (y redirige) si el usuario no tiene el rol que la página requiere
function protegerPagina(rolRequerido) {
  const rol = Sesion.rol();
  if (!rol) location.href = '/login/';
  else if (rol !== rolRequerido) location.href = '/';
  return rol === rolRequerido;
}

/* ---- Menú superior según el rol del token ---- */
async function cerrarSesion() {
  // El servidor invalida el refresh token y borra la cookie. El carro NO se pierde: está en PostgreSQL.
  await api('/api/auth/logout/', { method: 'POST', body: {} });
  Sesion.limpiar();
  location.href = '/';
}

function pintarMenu() {
  const rol = Sesion.rol();
  let html = '<a href="/eventos/">Eventos</a>';
  if (!rol) html += '<a href="/login/">Ingresar</a><a class="btn" href="/registro/">Crear cuenta</a>';
  if (rol === 'ESPECTADOR') html += '<a href="/carro/">Mi carro</a><a href="/mis-entradas/">Mis entradas</a>';
  if (rol === 'ORGANIZADOR') html += '<a href="/organizador/">Panel del organizador</a>';
  if (rol) html += `<span class="usuario">${esc(Sesion.claims().username)}</span><button class="link" id="salir">Salir</button>`;
  $('#menu').innerHTML = html;
  if (rol) $('#salir').addEventListener('click', cerrarSesion);
}

// Al cargar cualquier página: recupera la sesión (si existe) y dibuja el menú
Sesion.lista = Sesion.renovar().then(pintarMenu);

/* ---- Tarjeta de evento con forma de entrada (landing y catálogo) ---- */
function tarjetaEvento(e) {
  const d = new Date(e.fecha_hora);
  return `
    <a class="ticket" href="/eventos/${e.id}/">
      <div class="stub"><b>${d.getDate()}</b><span>${d.toLocaleString('es-CL', { month: 'short' })}</span></div>
      <div class="cuerpo">
        <span class="cat">${esc(e.categoria_display)}</span>
        <h3>${esc(e.nombre)}</h3>
        <p>${esc(e.artista)}</p>
        <p class="muted">${esc(e.recinto_detalle.nombre)}, ${esc(e.recinto_detalle.ciudad)}</p>
        <p class="precio">${e.precio_desde ? 'Desde ' + dinero(e.precio_desde) : 'Sin entradas a la venta'}</p>
      </div>
    </a>`;
}
