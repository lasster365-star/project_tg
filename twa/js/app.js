// Главный модуль Mini App.
(function () {
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try { tg.ready(); tg.expand(); } catch (_) {}
  }

  /** Простое состояние UI. */
  const state = {
    tab: "shop",
    categoryId: null,
    categoryTitle: "Все категории",
    product: null,
    deepLink: null,
  };

  function $(sel) { return document.querySelector(sel); }
  function el(tag, props = {}, children = []) {
    const e = document.createElement(tag);
    for (const k in props) {
      if (k === "class") e.className = props[k];
      else if (k === "html") e.innerHTML = props[k];
      else if (k === "text") e.textContent = props[k];
      else if (k.startsWith("on") && typeof props[k] === "function") {
        e.addEventListener(k.slice(2).toLowerCase(), props[k]);
      } else e.setAttribute(k, props[k]);
    }
    (Array.isArray(children) ? children : [children]).forEach(c => {
      if (c == null) return;
      if (typeof c === "string") e.appendChild(document.createTextNode(c));
      else e.appendChild(c);
    });
    return e;
  }

  function fmtPrice(text) {
    if (!text) return "—";
    return text;
  }

  function toast(text) {
    const t = $("#toast");
    t.textContent = text;
    t.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.add("hidden"), 1800);
  }

  async function onError(err) {
    console.error(err);
    if (err.status === 401) {
      renderText("Сессия истекла. Перезапустите мини-приложение через бота.");
      return;
    }
    toast(err.message || "Ошибка");
  }

  function renderText(text) {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text }));
  }

  // ---------- Экраны ----------
  function renderCategoryTabs(categories, activeId) {
    const tabs = el("div", { class: "tabs" });
    const all = el("button", {
      class: activeId == null ? "active" : "",
      onclick: () => loadProducts(null, "Все категории"),
      text: "Все",
    });
    tabs.appendChild(all);
    for (const cat of categories) {
      const btn = el("button", {
        class: cat.id === activeId ? "active" : "",
        onclick: () => loadProducts(cat.id, cat.title),
        text: cat.title,
      });
      tabs.appendChild(btn);
    }
    return tabs;
  }

  async function loadShop() {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text: "Загрузка…" }));
    try {
      const [catsRes, prodsRes] = await Promise.all([
        window.shopApi.categories(),
        window.shopApi.products(),
      ]);
      screen.innerHTML = "";
      screen.appendChild(el("div", { class: "section-title", text: "Категории" }));
      screen.appendChild(renderCategoryTabs(catsRes.categories, null));
      screen.appendChild(el("div", { class: "section-title", text: "Каталог" }));
      screen.appendChild(renderProductGrid(prodsRes.products));
    } catch (err) {
      onError(err);
    }
  }

  async function loadProducts(categoryId, categoryTitle) {
    state.categoryId = categoryId;
    state.categoryTitle = categoryTitle || "Все категории";
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text: "Загрузка…" }));
    try {
      const [catsRes, prodsRes] = await Promise.all([
        window.shopApi.categories(),
        window.shopApi.products(categoryId),
      ]);
      screen.innerHTML = "";
      const back = el("div", { class: "section-title", text: "← " + state.categoryTitle });
      back.style.cursor = "pointer";
      back.onclick = () => setTab("shop");
      screen.appendChild(back);
      screen.appendChild(renderCategoryTabs(catsRes.categories, categoryId));
      screen.appendChild(el("div", { class: "section-title", text: "Товары" }));
      if (!prodsRes.products.length) {
        screen.appendChild(el("div", { class: "empty", text: "Пока ничего нет" }));
      } else {
        screen.appendChild(renderProductGrid(prodsRes.products));
      }
    } catch (err) {
      onError(err);
    }
  }

  function renderProductGrid(products) {
    const grid = el("div", { class: "grid" });
    for (const p of products) {
      grid.appendChild(productCard(p));
    }
    return grid;
  }

  function coverLetters(title, kind) {
    if (kind === "subscription") return "★";
    if (kind === "account")     return "👤";
    if (kind === "key")         return "🔑";
    if (kind === "rental")      return "⏳";
    return (title || "?").slice(0, 1).toUpperCase();
  }

  function productCard(p) {
    const card = el("div", { class: "card", onclick: () => openProduct(p.id) });
    const cover = el("div", {
      class: "cover " + (p.kind || "kind-unknown"),
      text: coverLetters(p.title, p.kind),
    });
    card.appendChild(cover);
    const body = el("div", { class: "body" });
    body.appendChild(el("div", { class: "title", text: p.title }));
    body.appendChild(el("div", {
      class: "meta",
      text: "⭐ " + p.rating.toFixed(2) + " · " + p.reviewsCount + " отзывов",
    }));
    body.appendChild(el("div", { class: "price", text: fmtPrice(p.price) + " ₽" }));
    card.appendChild(body);
    return card;
  }

  async function openProduct(id) {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text: "Загрузка…" }));
    try {
      const res = await window.shopApi.product(id);
      const p = res.product;
      state.product = p;
      const back = el("div", {
        class: "section-title",
        text: "← " + state.categoryTitle,
      });
      back.style.cursor = "pointer";
      back.onclick = () => setTab("shop");
      screen.innerHTML = "";
      screen.appendChild(back);
      const card = el("div", { class: "card" });
      const cover = el("div", {
        class: "cover " + (p.kind || "kind-unknown"),
        text: coverLetters(p.title, p.kind),
      });
      card.appendChild(cover);
      const body = el("div", { class: "body" });
      body.appendChild(el("div", { class: "title", text: p.title }));
      body.appendChild(el("div", { class: "price", text: fmtPrice(p.price) + " ₽" }));
      body.appendChild(el("div", {
        class: "meta",
        text: "⭐ " + p.rating.toFixed(2) + " · " + p.reviewsCount + " отзывов",
      }));
      body.appendChild(el("div", {
        class: "meta",
        text: p.rentalDays
          ? ("Срок проката: " + p.rentalDays + " дней")
          : ("В наличии: " + (p.stock < 0 ? "∞" : p.stock)),
      }));
      card.appendChild(body);

      const addBtn = el("button", {
        class: "btn",
        text: "Добавить в корзину",
        onclick: async () => {
          try {
            const r = await window.shopApi.cartAdd(p.id, 1);
            toast("Добавлено. В корзине: " + r.quantity);
          } catch (err) { onError(err); }
        },
      });
      const backBtn = el("button", {
        class: "btn secondary",
        text: "Назад",
        onclick: () => setTab("shop"),
      });
      screen.appendChild(card);
      screen.appendChild(el("div", { class: "section-title", text: "Описание" }));
      screen.appendChild(el("div", { class: "meta", text: p.description, style: "padding:0 4px; color:var(--fg); font-size:14px; line-height:1.5;" }));
      screen.appendChild(el("div", { style: "margin-top:14px; display:flex; flex-direction:column; gap:8px;" }, [addBtn, backBtn]));
    } catch (err) {
      onError(err);
    }
  }

  async function loadCart() {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text: "Загрузка…" }));
    try {
      const res = await window.shopApi.cart();
      screen.innerHTML = "";
      screen.appendChild(el("div", { class: "section-title", text: "Корзина" }));
      if (!res.lines.length) {
        screen.appendChild(el("div", { class: "empty", text: "Корзина пуста" }));
        screen.appendChild(el("button", {
          class: "btn",
          text: "К покупкам",
          onclick: () => setTab("shop"),
        }));
        return;
      }
      for (const line of res.lines) {
        screen.appendChild(cartRow(line));
      }
      const totals = el("div", { class: "cart-totals" });
      totals.appendChild(el("div", {}, [
        "Итого: ", el("b", { text: fmtPrice(res.total) + " ₽" })
      ]));
      screen.appendChild(totals);
      const openBot = tg
        ? el("button", {
            class: "btn ghost",
            text: "💬 Открыть в боте для оплаты",
            onclick: () => {
              const bot = (tg.initDataUnsafe && tg.initDataUnsafe.user && tg.initDataUnsafe.user.username) || "";
              tg.openTelegramLink("https://t.me/" + (window.__BOT_USERNAME__ || "your_bot") + "?startapp=cart");
            },
          })
        : null;
      screen.appendChild(el("button", {
        class: "btn",
        text: "💳 Оплатить через бот",
        onclick: async () => {
          try {
            const r = await window.shopApi.checkout();
            const id = r.order.id;
            // Перенаправляем в бот: пользователь увидит тот же заказ
            if (tg) {
              const url = "https://t.me/" + (window.__BOT_USERNAME__ || "your_bot") + "?startapp=pay_" + id;
              tg.openTelegramLink(url);
              tg.close();
            } else {
              toast("Откройте приложение в Telegram для оплаты");
            }
          } catch (err) { onError(err); }
        },
      }));
      screen.appendChild(el("button", {
        class: "btn secondary",
        text: "Очистить корзину",
        onclick: async () => {
          try { await window.shopApi.cartClear(); toast("Очищено"); loadCart(); }
          catch (err) { onError(err); }
        },
      }));
      screen.appendChild(el("button", {
        class: "btn ghost",
        text: "⬅️ В магазин",
        onclick: () => setTab("shop"),
      }));
      if (openBot) screen.appendChild(openBot);
    } catch (err) { onError(err); }
  }

  function cartRow(line) {
    const row = el("div", { class: "cart-row" });
    row.appendChild(el("div", { class: "name", text: line.product.title }));
    const qty = el("div", { class: "qty", text: "× " + line.quantity + " · " + fmtPrice(line.subtotal) + " ₽" });
    row.appendChild(qty);
    const inc = el("button", { class: "rm", text: "+", onclick: async (e) => {
      e.stopPropagation();
      try { await window.shopApi.cartQty(line.product.id, line.quantity + 1); loadCart(); }
      catch (err) { onError(err); }
    } });
    const dec = el("button", { class: "rm", text: "−", onclick: async (e) => {
      e.stopPropagation();
      try { await window.shopApi.cartQty(line.product.id, line.quantity - 1); loadCart(); }
      catch (err) { onError(err); }
    } });
    const rm = el("button", { class: "rm", text: "🗑", onclick: async (e) => {
      e.stopPropagation();
      try { await window.shopApi.cartRemove(line.product.id); loadCart(); }
      catch (err) { onError(err); }
    } });
    row.appendChild(dec);
    row.appendChild(inc);
    row.appendChild(rm);
    return row;
  }

  async function loadProfile() {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text: "Загрузка…" }));
    try {
      const meRes = await window.shopApi.me();
      const topupsRes = await window.shopApi.topups();
      const ordersRes = await window.shopApi.orders();
      const u = meRes.user;
      screen.innerHTML = "";
      const card = el("div", { class: "profile-card" });
      card.appendChild(profileRow("Имя", u.fullName));
      card.appendChild(profileRow("Username", u.username ? ("@" + u.username) : "—"));
      card.appendChild(profileRow("Рефералов", String(u.referrals)));
      card.appendChild(profileRow("Баланс", fmtPrice(u.balance) + " ₽"));
      card.appendChild(profileRow("Реф-код", u.refCode));
      screen.appendChild(card);

      const amounts = [300, 500, 1000, 2000, 5000];
      const row = el("div", { style: "display:flex; flex-wrap:wrap; gap:8px;" });
      for (const a of amounts) {
        row.appendChild(el("button", {
          class: "btn secondary",
          style: "flex:1 0 30%; padding:10px;",
          text: "+" + a + " ₽",
          onclick: async () => {
            try {
              const r = await window.shopApi.topup(a);
              toast("Баланс: " + fmtPrice(r.user.balance) + " ₽");
              loadProfile();
            } catch (err) { onError(err); }
          },
        }));
      }
      screen.appendChild(el("div", { class: "section-title", text: "Пополнить баланс" }));
      screen.appendChild(row);

      screen.appendChild(el("div", { class: "section-title", text: "История покупок" }));
      if (!ordersRes.orders.length) {
        screen.appendChild(el("div", { class: "empty", text: "Пока пусто" }));
      } else {
        for (const o of ordersRes.orders) {
          const item = el("div", { class: "profile-card" });
          item.appendChild(profileRow("Заказ", "#" + o.id + " · " + o.status));
          const subtotal = o.items.reduce((acc, i) => acc + Number(i.subtotal), 0);
          item.appendChild(profileRow("Сумма", fmtPrice(subtotal) + " ₽"));
          item.appendChild(profileRow("Товаров", String(o.items.length)));
          screen.appendChild(item);
        }
      }

      screen.appendChild(el("div", { class: "section-title", text: "Пополнения" }));
      if (!topupsRes.topups.length) {
        screen.appendChild(el("div", { class: "empty", text: "Нет пополнений" }));
      } else {
        for (const t of topupsRes.topups) {
          const item = el("div", { class: "profile-card" });
          item.appendChild(profileRow("Сумма", "+" + fmtPrice(t.amount) + " ₽"));
          item.appendChild(profileRow("Метод", t.method));
          item.appendChild(profileRow("Когда", new Date(t.createdAt).toLocaleString()));
          screen.appendChild(item);
        }
      }
    } catch (err) { onError(err); }
  }

  function profileRow(label, value) {
    const row = el("div", { class: "row" });
    row.appendChild(el("span", { text: label }));
    row.appendChild(el("span", { class: "v", text: value }));
    return row;
  }

  async function loadSupport() {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "section-title", text: "Поддержка" }));
    const card = el("div", { class: "profile-card" });
    card.appendChild(el("div", { class: "row" }, [
      el("span", { text: "Связаться" }),
    ]));
    const note = el("div", {
      class: "meta",
      text: "Среднее время ответа — 15 минут в рабочее время.",
    });
    screen.appendChild(card);
    screen.appendChild(note);
    screen.appendChild(el("button", {
      class: "btn",
      text: "Открыть чат поддержки",
      onclick: () => {
        if (tg) tg.openTelegramLink("https://t.me/" + (window.__SUPPORT_USERNAME__ || "your_support"));
        else window.open("https://t.me/" + (window.__SUPPORT_USERNAME__ || "your_support"));
      },
    }));
  }

  // ---------- Роутер вкладок ----------
  function setTab(name) {
    state.tab = name;
    document.querySelectorAll(".bottombar button").forEach(b => {
      b.classList.toggle("active", b.dataset.tab === name);
    });
    const title = $("#title");
    const backBtn = $("#backBtn");
    backBtn.classList.add("hidden");
    if (name === "shop")    { title.textContent = "Магазин"; loadShop(); }
    if (name === "cart")    { title.textContent = "Корзина"; loadCart(); }
    if (name === "profile") { title.textContent = "Кабинет"; loadProfile(); }
    if (name === "support") { title.textContent = "Поддержка"; loadSupport(); }
  }

  // ---------- Старт ----------
  function bind() {
    document.querySelectorAll(".bottombar button").forEach(b => {
      b.addEventListener("click", () => setTab(b.dataset.tab));
    });
    $("#backBtn").addEventListener("click", () => {
      if (state.product) { state.product = null; setTab(state.categoryId ? "shop" : "shop"); }
    });
    $("#cartBtn").addEventListener("click", () => setTab("cart"));
  }

  function handleDeepLink() {
    // tg.initDataUnsafe.start_param может прийти, например "cart" или "pay_<id>"
    const unsafe = tg && tg.initDataUnsafe ? tg.initDataUnsafe : null;
    const param = unsafe && unsafe.start_param ? unsafe.start_param : null;
    if (!param) return;
    if (param === "cart") setTab("cart");
    else if (param.startsWith("pay_")) {
      const id = parseInt(param.slice(4), 10);
      if (!Number.isNaN(id)) {
        window.shopApi.payOrder(id)
          .then(() => toast("Заказ #" + id + " оплачен"))
          .catch(err => onError(err))
          .finally(() => setTab("profile"));
      }
    }
  }

  // Стартовая загрузка
    bind();
    // Если initData пустое (например браузер) — покажем дружелюбное сообщение
    // вместо «сессия истекла».
    if (!tg || !window.shopApi.initData()) {
      const screen = $("#screen");
      screen.innerHTML = "";
      const note = document.createElement("div");
      note.className = "empty";
      note.innerHTML =
        '<div style="font-size:48px; margin-bottom:12px;">🛍</div>' +
        '<div style="font-size:18px; font-weight:600; color:var(--fg); margin-bottom:8px;">Добро пожаловать в магазин!</div>' +
        '<div style="margin-bottom:14px;">Откройте приложение через Telegram-бот, чтобы войти и купить.</div>' +
        '<div class="muted" style="margin-top:18px;">Раздел «Магазин» доступен без входа — нажмите вкладку ниже.</div>';
      screen.appendChild(note);
      // Витрина всё равно подгружается (через /api/public/*).
      // Оверрайдим api.* чтобы не падать на 401.
      const proxy = window.shopApi;
      const origMe = proxy.me.bind(proxy);
      const origCart = proxy.cart.bind(proxy);
      proxy.me = async () => ({ user: null });
      proxy.cart = async () => ({ lines: [], total: "0.00" });
      proxy.orders = async () => ({ orders: [] });
      proxy.topups = async () => ({ topups: [] });
      proxy.topup = async () => { throw new Error("войдите через бота"); };
      proxy.cartAdd = async () => { throw new Error("войдите через бота"); };
      proxy.cartQty = async () => { throw new Error("войдите через бота"); };
      proxy.cartRemove = async () => { throw new Error("войдите через бота"); };
      proxy.cartClear = async () => { throw new Error("войдите через бота"); };
      proxy.checkout = async () => { throw new Error("войдите через бота"); };
      proxy.payOrder = async () => { throw new Error("войдите через бота"); };
      proxy.cancelOrder = async () => { throw new Error("войдите через бота"); };
      void origMe; void origCart;

      // Подменяем API URL категорий/товаров на публичный.
      proxy.categories = async () => (await fetch("/api/public/categories")).json();
      proxy.products = async (cid, kind) => {
        const q = new URLSearchParams();
        if (cid != null) q.set("categoryId", String(cid));
        if (kind) q.set("kind", kind);
        const u = "/api/public/products" + (q.toString() ? "?" + q.toString() : "");
        return (await fetch(u)).json();
      };
      return;
    }
    setTab("shop");
    handleDeepLink();
})();
