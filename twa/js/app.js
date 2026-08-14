// Главный модуль Mini App.
(function () {
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
  if (tg) {
    try { tg.ready(); tg.expand(); } catch (_) {}
  }

  const state = {
    tab: "shop",
    categoryId: null,
    categoryTitle: "Все категории",
    product: null,
    deepLink: null,
    guestMode: false,        // initData есть, но без поля user
    noInitData: false,       // initData отсутствует вовсе
    initInfo: null,
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
      // тихо обработаем — гость может смотреть витрину
      return null;
    }
    toast(err.message || "Ошибка");
    return null;
  }

  function renderText(text) {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text }));
  }

  // ---------- Диагностика ----------
  async function probeInitData() {
    const raw = window.shopApi.initData();
    state.noInitData = !raw;
    if (!raw) {
      state.initInfo = { raw_present: false };
      return state.initInfo;
    }
    try {
      const r = await fetch("/api/debug/initdata", {
        headers: { Authorization: "tma " + raw },
      });
      const data = await r.json();
      state.initInfo = data;
      state.guestMode = !!(
        data.validation_ok &&
        (!data.user || !data.user.id)
      );
      return data;
    } catch (err) {
      console.warn("probeInitData failed", err);
      return null;
    }
  }

  function renderInitBanner() {
    // На главном экране: тонкая плашка с диагностикой.
    const screen = $("#screen");
    let banner = document.getElementById("initBanner");
    if (!state.initInfo || !state.noInitData && !state.guestMode) {
      if (banner) banner.remove();
      return;
    }
    const html = state.noInitData
      ? '<div class="banner warn">⚠️ Telegram не передал данные. Открой бота → нажми <b>🛍 Открыть магазин</b>.</div>'
      : '<div class="banner warn">⚠️ Mini App запущен в режиме inline — Telegram не передал <code>user</code>. Открой через reply-кнопку <b>🛍 Открыть магазин</b>.</div>';
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "initBanner";
      screen.insertBefore(banner, screen.firstChild);
    }
    banner.innerHTML = html;
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
    renderInitBanner();
    try {
      const [catsRes, prodsRes] = await Promise.all([
        window.shopApi.categories(),
        window.shopApi.products(),
      ]);
      screen.innerHTML = "";
      renderInitBanner();
      screen.appendChild(el("div", { class: "section-title", text: "Категории" }));
      screen.appendChild(renderCategoryTabs(catsRes.categories, null));
      screen.appendChild(el("div", { class: "section-title", text: "Каталог" }));
      screen.appendChild(renderProductGrid(prodsRes.products));
    } catch (err) {
      await onError(err);
      // Не падаем в пустой экран: покажем хотя бы витрину.
      try {
        const catsRes = await fetch("/api/public/categories").then(r => r.json());
        const prodsRes = await fetch("/api/public/products").then(r => r.json());
        screen.innerHTML = "";
        renderInitBanner();
        screen.appendChild(el("div", { class: "section-title", text: "Категории" }));
        screen.appendChild(renderCategoryTabs(catsRes.categories, null));
        screen.appendChild(el("div", { class: "section-title", text: "Каталог" }));
        if (!prodsRes.products.length) {
          screen.appendChild(el("div", { class: "empty", text: "Каталог пуст" }));
        } else {
          screen.appendChild(renderProductGrid(prodsRes.products));
        }
      } catch (e2) {
        renderText("Не удалось загрузить каталог. Попробуйте позже.");
      }
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
      renderInitBanner();
      screen.appendChild(renderCategoryTabs(catsRes.categories, categoryId));
      screen.appendChild(el("div", { class: "section-title", text: "Товары" }));
      if (!prodsRes.products.length) {
        screen.appendChild(el("div", { class: "empty", text: "Пока ничего нет" }));
      } else {
        screen.appendChild(renderProductGrid(prodsRes.products));
      }
    } catch (err) {
      await onError(err);
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
      renderInitBanner();
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
      card.appendChild(card.children[0]);

      const card2 = el("div", { class: "card" });
      const cover2 = el("div", {
        class: "cover " + (p.kind || "kind-unknown"),
        text: coverLetters(p.title, p.kind),
      });
      card2.appendChild(cover2);
      const body2 = el("div", { class: "body" });
      body2.appendChild(el("div", { class: "title", text: p.title }));
      body2.appendChild(el("div", { class: "price", text: fmtPrice(p.price) + " ₽" }));
      body2.appendChild(el("div", {
        class: "meta",
        text: "⭐ " + p.rating.toFixed(2) + " · " + p.reviewsCount + " отзывов",
      }));
      body2.appendChild(el("div", {
        class: "meta",
        text: p.rentalDays
          ? ("Срок проката: " + p.rentalDays + " дней")
          : ("В наличии: " + (p.stock < 0 ? "∞" : p.stock)),
      }));
      card2.appendChild(body2);

      const addBtn = el("button", {
        class: "btn",
        text: "Добавить в корзину",
        onclick: async () => {
          try {
            const r = await window.shopApi.cartAdd(p.id, 1);
            toast("Добавлено. В корзине: " + r.quantity);
          } catch (err) { await onError(err); toast("Открой бота заново"); }
        },
      });
      const backBtn = el("button", {
        class: "btn secondary",
        text: "Назад",
        onclick: () => setTab("shop"),
      });
      screen.appendChild(card2);
      screen.appendChild(el("div", { class: "section-title", text: "Описание" }));
      screen.appendChild(el("div", { class: "meta", text: p.description, style: "padding:0 4px; color:var(--fg); font-size:14px; line-height:1.5;" }));
      screen.appendChild(el("div", { style: "margin-top:14px; display:flex; flex-direction:column; gap:8px;" }, [addBtn, backBtn]));
    } catch (err) {
      await onError(err);
    }
  }

  async function loadCart() {
    const screen = $("#screen");
    screen.innerHTML = "";
    screen.appendChild(el("div", { class: "empty", text: "Загрузка…" }));
    renderInitBanner();
    try {
      const res = await window.shopApi.cart();
      screen.innerHTML = "";
      renderInitBanner();
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
      screen.appendChild(el("button", {
        class: "btn",
        text: "💳 Оплатить через бот",
        onclick: async () => {
          try {
            const r = await window.shopApi.checkout();
            const id = r.order.id;
            if (tg) {
              const url = "https://t.me/" + (window.__BOT_USERNAME__ || "your_bot") + "?startapp=pay_" + id;
              tg.openTelegramLink(url);
              tg.close();
            } else {
              toast("Откройте приложение в Telegram для оплаты");
            }
          } catch (err) { await onError(err); toast("Открой бота заново"); }
        },
      }));
      screen.appendChild(el("button", {
        class: "btn secondary",
        text: "Очистить корзину",
        onclick: async () => {
          try { await window.shopApi.cartClear(); toast("Очищено"); loadCart(); }
          catch (err) { await onError(err); }
        },
      }));
      screen.appendChild(el("button", {
        class: "btn ghost",
        text: "⬅️ В магазин",
        onclick: () => setTab("shop"),
      }));
    } catch (err) { await onError(err); }
  }

  function cartRow(line) {
    const row = el("div", { class: "cart-row" });
    row.appendChild(el("div", { class: "name", text: line.product.title }));
    row.appendChild(el("div", { class: "qty", text: "× " + line.quantity + " · " + fmtPrice(line.subtotal) + " ₽" }));
    const dec = el("button", { class: "rm", text: "−", onclick: async (e) => {
      e.stopPropagation();
      try { await window.shopApi.cartQty(line.product.id, line.quantity - 1); loadCart(); }
      catch (err) { await onError(err); }
    } });
    const inc = el("button", { class: "rm", text: "+", onclick: async (e) => {
      e.stopPropagation();
      try { await window.shopApi.cartQty(line.product.id, line.quantity + 1); loadCart(); }
      catch (err) { await onError(err); }
    } });
    const rm = el("button", { class: "rm", text: "🗑", onclick: async (e) => {
      e.stopPropagation();
      try { await window.shopApi.cartRemove(line.product.id); loadCart(); }
      catch (err) { await onError(err); }
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
    renderInitBanner();
    try {
      const meRes = await window.shopApi.me();
      const u = meRes.user;
      screen.innerHTML = "";
      renderInitBanner();
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
            } catch (err) { await onError(err); }
          },
        }));
      }
      screen.appendChild(el("div", { class: "section-title", text: "Пополнить баланс" }));
      screen.appendChild(row);

      screen.appendChild(el("div", { class: "section-title", text: "История покупок" }));
      try {
        const ordersRes = await window.shopApi.orders();
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
      } catch (e) {
        screen.appendChild(el("div", { class: "empty", text: "История недоступна" }));
      }

      screen.appendChild(el("div", { class: "section-title", text: "Пополнения" }));
      try {
        const topupsRes = await window.shopApi.topups();
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
      } catch (e) {
        screen.appendChild(el("div", { class: "empty", text: "История недоступна" }));
      }
    } catch (err) { await onError(err); }
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
    renderInitBanner();
    screen.appendChild(el("div", { class: "section-title", text: "Поддержка" }));
    const card = el("div", { class: "profile-card" });
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

  async function main() {
      bind();
      if (!tg || !window.shopApi.initData()) {
        state.noInitData = true;
        const screen = $("#screen");
        screen.innerHTML = "";
        const note = document.createElement("div");
        note.className = "empty";
        note.innerHTML =
          '<div style="font-size:48px; margin-bottom:12px;">🛍</div>' +
          '<div style="font-size:18px; font-weight:600; color:var(--fg); margin-bottom:8px;">Добро пожаловать в магазин!</div>' +
          '<div style="margin-bottom:14px;">Откройте приложение через Telegram-бот, чтобы войти и купить.</div>';
        // Кнопка — глубокая ссылка на бота. Если бот известен — открываем.
        const botName = (window.__BOT_USERNAME__ || "your_bot").replace(/^@/, "");
        screen.appendChild(note);
        const open = el("button", {
          class: "btn",
          text: "Открыть в Telegram-боте",
          onclick: () => {
            const url = "https://t.me/" + botName + "?startapp=shop";
            window.open(url, "_blank");
          },
        });
        screen.appendChild(open);
        return;
      }
      await probeInitData();
      if (state.noInitData) {
        // no-op
      } else if (state.guestMode || !state.initInfo || !state.initInfo.user) {
        installGuestProxy();
        setTab("shop");
        handleDeepLink();
      } else {
        setTab("shop");
        handleDeepLink();
      }
    }

  function installGuestProxy() {
    // Гость: витрина видна, но приватные эндпоинты кидают «войди через бота»
    const proxy = window.shopApi;
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
    // Категории и товары — публичные
    proxy.categories = async () => (await fetch("/api/public/categories")).json();
    proxy.products = async (cid, kind) => {
      const q = new URLSearchParams();
      if (cid != null) q.set("categoryId", String(cid));
      if (kind) q.set("kind", kind);
      const u = "/api/public/products" + (q.toString() ? "?" + q.toString() : "");
      return (await fetch(u)).json();
    };
    proxy.product = async (id) => (await fetch(`/api/public/product/${id}`)).json();
  }

  main();
})();
