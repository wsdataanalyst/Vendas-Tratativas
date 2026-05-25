document.querySelectorAll("[data-open]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-open");
    const dialog = document.getElementById(id);
    if (dialog) dialog.showModal();
  });
});

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const dialog = btn.closest("dialog");
    if (dialog) dialog.close();
  });
});

document.querySelectorAll(".modal").forEach((dialog) => {
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });
});

function atualizarCamposPerda(form) {
  const statusSel = form.querySelector(".sel-status-negocio");
  const chkConv = form.querySelector(".chk-convertido");
  const camposPerda = form.querySelector(".campos-perda");
  const campoTrat = form.querySelector(".campo-tratativa");
  const campoConc = form.querySelector(".campo-concorrencia");
  const selTrat = form.querySelector(".sel-id-tratativa");
  const inpConc = form.querySelector(".inp-concorrencia");
  const motivoRadios = form.querySelectorAll('input[name="motivo_perda"]');

  let mostrar = false;
  if (statusSel) {
    mostrar = statusSel.value === "Perdido";
  } else if (chkConv) {
    mostrar = !chkConv.checked;
  }

  if (camposPerda) camposPerda.style.display = mostrar ? "block" : "none";

  let motivo = "tratativa";
  motivoRadios.forEach((r) => {
    if (r.checked) motivo = r.value;
  });

  if (campoTrat) campoTrat.style.display = motivo === "tratativa" && mostrar ? "flex" : "none";
  if (campoConc) campoConc.style.display = motivo === "concorrencia" && mostrar ? "flex" : "none";
  if (selTrat) selTrat.required = mostrar && motivo === "tratativa";
  if (inpConc) inpConc.required = mostrar && motivo === "concorrencia";

  if (chkConv && chkConv.checked) {
    if (selTrat) selTrat.value = "";
    if (inpConc) inpConc.value = "";
  }
}

window.atualizarCamposPerda = atualizarCamposPerda;

function bindFormPerda(form) {
  const statusSel = form.querySelector(".sel-status-negocio");
  const chk = form.querySelector(".chk-convertido");
  if (statusSel) statusSel.addEventListener("change", () => atualizarCamposPerda(form));
  if (chk) chk.addEventListener("change", () => atualizarCamposPerda(form));
  form.querySelectorAll('input[name="motivo_perda"]').forEach((r) => {
    r.addEventListener("change", () => atualizarCamposPerda(form));
  });
  atualizarCamposPerda(form);
}

document.querySelectorAll(".form-negocio, .form-venda").forEach(bindFormPerda);

function atualizarFormPerformance(form) {
  const sel = form.querySelector(".sel-status-perf");
  const campoPrev = form.querySelector(".campo-previsao");
  const inpPrev = form.querySelector(".inp-previsao");
  const camposPerda = form.querySelector(".campos-perda-perf");
  const campoConc = form.querySelector(".campo-concorrencia-perf");
  const inpConc = form.querySelector(".inp-concorrencia-perf");
  if (!sel) return;
  const st = sel.value;
  if (campoPrev) campoPrev.style.display = st === "Em andamento" ? "flex" : "none";
  if (inpPrev) inpPrev.required = st === "Em andamento";
  if (camposPerda) camposPerda.style.display = st === "Negócio perdido" ? "block" : "none";
  if (campoConc) campoConc.style.display = st === "Negócio perdido" ? "flex" : "none";
  if (inpConc) inpConc.required = st === "Negócio perdido";
}

window.atualizarFormPerformance = atualizarFormPerformance;

document.querySelectorAll(".form-performance").forEach((form) => {
  const sel = form.querySelector(".sel-status-perf");
  if (sel) {
    sel.addEventListener("change", () => atualizarFormPerformance(form));
    atualizarFormPerformance(form);
  }
});

const SITUACOES_CODIGO_ITEM = window.SITUACOES_CODIGO_ITEM || [
  "Falta de estoque produto indispensavel",
];

function situacaoExigeCodigo(situacao) {
  return SITUACOES_CODIGO_ITEM.includes(situacao);
}

function atualizarCampoCodigoItem(form) {
  const sel = form.querySelector(".sel-situacao");
  const campo = form.querySelector(".campo-codigo-item");
  const inp = form.querySelector(".inp-codigo-item");
  if (!sel || !campo) return;
  const exige = situacaoExigeCodigo(sel.value);
  campo.style.display = exige ? "flex" : "none";
  if (inp) {
    inp.required = exige;
    if (!exige) inp.value = "";
  }
}

window.atualizarCampoCodigoItem = atualizarCampoCodigoItem;

function bindFormTratativa(form) {
  const sel = form.querySelector(".sel-situacao");
  if (sel) {
    sel.addEventListener("change", () => atualizarCampoCodigoItem(form));
    atualizarCampoCodigoItem(form);
  }
}

document.querySelectorAll(".form-tratativa").forEach(bindFormTratativa);

function atualizarBadges(contagens) {
  if (!contagens) return;
  const map = [
    { href: "/vendas-performance", key: "performance_em_andamento", cls: "" },
    { href: "/tratativas", key: "tratativas_abertas", cls: "warn" },
  ];
  map.forEach(({ href, key, cls }) => {
    const link = document.querySelector(`.nav-links a[href="${href}"]`);
    if (!link) return;
    let badge = link.querySelector(".nav-badge");
    const n = contagens[key] || 0;
    if (n > 0) {
      if (!badge) {
        badge = document.createElement("span");
        badge.className = "nav-badge" + (cls ? " " + cls : "");
        link.appendChild(badge);
      }
      badge.textContent = n;
    } else if (badge) {
      badge.remove();
    }
  });
}

(function initSync() {
  const body = document.body;
  if (!body.hasAttribute("data-sync-version")) return;

  let lastVersion = body.dataset.syncVersion || "";
  const POLL_MS = 5000;

  async function poll() {
    try {
      const res = await fetch(
        `/api/sync?since=${encodeURIComponent(lastVersion)}`,
        { credentials: "same-origin", cache: "no-store" }
      );
      if (!res.ok) return;
      const data = await res.json();
      if (!data.version) return;
      if (lastVersion && data.changed && data.version !== lastVersion) {
        window.location.reload();
        return;
      }
      lastVersion = data.version;
      if (data.contagens) atualizarBadges(data.contagens);
    } catch (_) {
      /* rede instável — próxima tentativa */
    }
  }

  setInterval(poll, POLL_MS);
})();
