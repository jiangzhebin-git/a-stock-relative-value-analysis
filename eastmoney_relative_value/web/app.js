const gate = document.querySelector("#loginGate");
const form = document.querySelector("#loginForm");
const pinInput = document.querySelector("#pinInput");
const loginError = document.querySelector("#loginError");
const refreshButton = document.querySelector("#refreshButton");
const grid = document.querySelector("#stockGrid");
const template = document.querySelector("#stockCardTemplate");

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, "0")).join("");
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  const expected = window.DASHBOARD_CONFIG?.pinHash || "";
  if (!expected) {
    loginError.textContent = "网页PIN尚未在部署配置中启用";
    return;
  }
  if (await sha256(pinInput.value) === expected) {
    sessionStorage.setItem("marketPulseUnlocked", "1");
    gate.classList.add("hidden");
    loadSnapshot();
  } else {
    loginError.textContent = "PIN不正确，请重新输入";
    pinInput.select();
  }
});

if (sessionStorage.getItem("marketPulseUnlocked") === "1") {
  gate.classList.add("hidden");
  loadSnapshot();
}

function money(value) { return Number(value).toFixed(2); }
function percent(value) { return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`; }

function renderStock(stock, index) {
  const node = template.content.cloneNode(true);
  const card = node.querySelector(".stock-card");
  const expensive = stock.deviation_pct > .02;
  const cheap = stock.deviation_pct < -.02;
  card.style.setProperty("--accent", expensive ? "var(--red)" : cheap ? "var(--green)" : "var(--amber)");
  card.style.animationDelay = `${index * 70}ms`;
  node.querySelector(".stock-code").textContent = stock.symbol;
  node.querySelector(".stock-name").textContent = stock.name;
  node.querySelector(".mode-badge").textContent = stock.mode === "dynamic_intraday" ? "动态盘中" : "日线回退";
  node.querySelector(".actual-price").textContent = `¥ ${money(stock.actual_price)}`;
  node.querySelector(".theory-price").textContent = `¥ ${money(stock.theoretical_price)}`;
  node.querySelector(".deviation").textContent = percent(stock.deviation_pct);
  node.querySelector(".deviation-level").textContent = stock.deviation_level;
  node.querySelector(".buy-zone").textContent = `${money(stock.buy_zones[2])} – ${money(stock.buy_zones[0])}`;
  node.querySelector(".sell-zone").textContent = `${money(stock.sell_zones[0])} – ${money(stock.sell_zones[2])}`;
  node.querySelector(".stop-price").textContent = money(stock.stop_loss_price);
  node.querySelector(".risk-confidence").textContent = `${stock.risk_level} / ${stock.confidence}`;
  node.querySelector(".card-note").textContent = stock.message;
  node.querySelector(".data-time").textContent = `行情 ${new Date(stock.data_time).toLocaleString("zh-CN")}`;
  return node;
}

async function loadSnapshot() {
  refreshButton.classList.add("loading");
  refreshButton.disabled = true;
  document.querySelector("#statusText").textContent = "正在读取最新快照";
  try {
    const response = await fetch(`live_snapshot.json?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const snapshot = await response.json();
    grid.replaceChildren(...snapshot.stocks.map(renderStock));
    const updated = new Date(snapshot.generated_at);
    const ageMinutes = Math.max(0, (Date.now() - updated.getTime()) / 60000);
    document.querySelector("#updateTime").textContent = `更新于 ${updated.toLocaleString("zh-CN")}`;
    document.querySelector("#statusText").textContent =
      ageMinutes > 30 ? `数据已超过 ${Math.round(ageMinutes)} 分钟` : "数据已同步";
    document.querySelector(".status-dot").style.background = ageMinutes > 30 ? "var(--amber)" : "var(--green)";
    document.querySelector("#modelInfo").textContent =
      `统一模型快照：${new Date(snapshot.model_generated_at).toLocaleString("zh-CN")} ｜ 训练数据截至 ${snapshot.model_data_date}`;
  } catch (error) {
    document.querySelector("#statusText").textContent = `刷新失败：${error.message}`;
  } finally {
    refreshButton.classList.remove("loading");
    refreshButton.disabled = false;
  }
}

refreshButton.addEventListener("click", loadSnapshot);

