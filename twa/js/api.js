// Обёртка над /api. initData берётся из window.Telegram.WebApp.
(function (window) {
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

  function initData() {
    return tg && tg.initData ? tg.initData : "";
  }

  async function request(path, opts = {}) {
    const url = path.startsWith("http") ? path : path;
    const headers = Object.assign({}, opts.headers || {});
    const initDataRaw = initData();
    if (initDataRaw) {
      headers["Authorization"] = "tma " + initDataRaw;
    }
    const fetchOpts = {
      method: opts.method || "GET",
      headers,
    };
    if (opts.body !== undefined) {
      headers["Content-Type"] = "application/json";
      fetchOpts.body = JSON.stringify(opts.body);
    }
    const resp = await fetch(url, fetchOpts);
    let data = null;
    const txt = await resp.text();
    try { data = txt ? JSON.parse(txt) : null; } catch (_) { data = txt; }
    if (!resp.ok) {
      const err = new Error((data && data.detail) || ("HTTP " + resp.status));
      err.status = resp.status;
      err.body = data;
      throw err;
    }
    return data;
  }

  const api = {
    initData,
    raw: request,

    me: () => request("/api/me"),
    categories: (kind) => {
      const q = kind ? ("?kind=" + encodeURIComponent(kind)) : "";
      return request("/api/categories" + q);
    },
    products: (categoryId, kind) => {
      const params = [];
      if (categoryId != null) params.push("categoryId=" + categoryId);
      if (kind) params.push("kind=" + encodeURIComponent(kind));
      const q = params.length ? ("?" + params.join("&")) : "";
      return request("/api/products" + q);
    },
    product: (id) => request("/api/product/" + id),
    cart: () => request("/api/cart"),
    cartAdd: (productId, quantity = 1) =>
      request("/api/cart/add", { method: "POST", body: { productId, quantity } }),
    cartQty: (productId, quantity) =>
      request("/api/cart/qty", { method: "POST", body: { productId, quantity } }),
    cartRemove: (productId) =>
      request("/api/cart/remove", { method: "POST", body: { productId } }),
    cartClear: () => request("/api/cart/clear", { method: "POST", body: {} }),
    checkout: () => request("/api/orders/checkout", { method: "POST", body: {} }),
    payOrder: (id) => request("/api/orders/" + id + "/pay", { method: "POST", body: {} }),
    cancelOrder: (id) => request("/api/orders/" + id + "/cancel", { method: "POST", body: {} }),
    orders: () => request("/api/orders"),
    topup: (amount) =>
      request("/api/balance/topup", { method: "POST", body: { amount } }),
    topups: () => request("/api/topups"),
  };

  window.shopApi = api;
})(window);
