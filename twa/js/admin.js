// Минимальная админка: список товаров, создание нового, пополнение баланса.
(function () {
  const TOKEN_KEY = "tg_shop_admin_token";

  function getToken() { return localStorage.getItem(TOKEN_KEY) || ""; }
  function setToken(t) { localStorage.setItem(TOKEN_KEY, t); }

  async function api(path, opts = {}) {
    const headers = Object.assign({}, opts.headers || {});
    const t = getToken();
    if (t) headers["X-Admin-Token"] = t;
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    const r = await fetch(path, Object.assign({}, opts, { headers }));
    let data = null;
    try { data = await r.json(); } catch (_) { data = null; }
    if (!r.ok) {
      const msg = (data && data.detail) || ("HTTP " + r.status);
      throw new Error(msg);
    }
    return data;
  }

  function $(id) { return document.getElementById(id); }

  function show(panel) {
    $("loginBox").classList.toggle("hidden", panel !== "login");
    $("panel").classList.toggle("hidden", panel !== "panel");
  }

  async function login() {
    const tok = $("tok").value.trim();
    if (!tok) return;
    setToken(tok);
    try {
      await api("/api/admin/products");
      show("panel");
      loadProducts();
      loadUsers();
    } catch (err) {
      setToken("");
      alert("Неверный токен: " + err.message);
    }
  }

  function logout() {
    setToken("");
    show("login");
    $("tok").value = "";
  }

  function renderProduct(p) {
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <span>
        <span class="id">#${p.id}</span>
        <span class="title">${escapeHtml(p.title)}</span>
        <span class="muted"> · ${p.kind}</span>
      </span>
      <input class="price-edit" type="number" step="0.01" value="${p.price}" />
      <input class="stock-edit" type="number" value="${p.stock}" />
      <span>
        <button class="btn secondary save-btn">💾</button>
        <button class="btn danger delete-btn">🗑</button>
      </span>
    `;
    row.querySelector(".save-btn").onclick = async () => {
      const price = +row.querySelector(".price-edit").value;
      const stock = +row.querySelector(".stock-edit").value;
      try {
        await api(`/api/admin/products/${p.id}`, {
          method: "PATCH",
          body: { price, stock },
        });
        flash(row, "✅");
        loadUsers();
      } catch (err) { alert(err.message); }
    };
    row.querySelector(".delete-btn").onclick = async () => {
      if (!confirm(`Удалить товар #${p.id}?`)) return;
      try {
        await api(`/api/admin/products/${p.id}`, { method: "DELETE" });
        row.remove();
      } catch (err) { alert(err.message); }
    };
    return row;
  }

  function flash(row, text) {
    const span = document.createElement("span");
    span.textContent = text;
    span.style.marginLeft = "6px";
    row.appendChild(span);
    setTimeout(() => span.remove(), 1500);
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;",
      "\"": "&quot;", "'": "&#39;"
    }[c]));
  }

  async function loadProducts() {
    const list = $("products");
    list.innerHTML = "Загрузка…";
    try {
      const data = await api("/api/admin/products");
      list.innerHTML = "";
      data.products.forEach(p => list.appendChild(renderProduct(p)));
    } catch (err) {
      list.textContent = "Ошибка: " + err.message;
    }
  }

  async function loadUsers() {
    const list = $("users");
    list.innerHTML = "Загрузка…";
    // Мы не добавляли /api/admin/users в коде проекта — здесь простой GET /api/me не подойдёт.
    // Чтобы админский веб не падал, покажем заглушку:
    list.innerHTML = "Список пользователей с балансами — в личном кабинете каждого пользователя (через бота).";
  }

  // ====== Forms ======
  $("loginBtn") && ($("loginBtn").onclick = login);

  $("refreshProducts") && ($("refreshProducts").onclick = loadProducts);

  $("newProduct") && ($("newProduct").onsubmit = async (e) => {
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target).entries());
    const payload = {
      categoryId: +fd.categoryId,
      title: fd.title,
      description: fd.description || "",
      price: parseFloat(fd.price),
      kind: fd.kind,
      rentalDays: fd.rentalDays ? +fd.rentalDays : null,
      stock: fd.stock !== "" ? +fd.stock : -1,
    };
    try {
      const out = await api("/api/admin/products", { method: "POST", body: payload });
      $("newProductOut").textContent = `✅ Создан #${out.product.id}: ${out.product.title}`;
      e.target.reset();
      loadProducts();
    } catch (err) {
      $("newProductOut").textContent = "❌ " + err.message;
    }
  });

  $("topup") && ($("topup").onsubmit = async (e) => {
    e.preventDefault();
    const fd = Object.fromEntries(new FormData(e.target).entries());
    try {
      const out = await api("/api/admin/users/topup", {
        method: "POST",
        body: { telegramId: +fd.telegramId, amount: parseFloat(fd.amount) },
      });
      $("topupOut").textContent =
        `✅ ${out.user.fullName}: баланс = ${out.user.balance} ₽`;
      e.target.reset();
    } catch (err) {
      $("topupOut").textContent = "❌ " + err.message;
    }
  });

  // Auto-login if token already present
  if (getToken()) {
    show("panel");
    loadProducts();
    loadUsers();
  } else {
    show("login");
  }
})();
