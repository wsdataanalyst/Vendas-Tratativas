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

function atualizarCampoPerda(form) {
  const chk = form.querySelector(".chk-convertido");
  const campo = form.querySelector(".campo-id-perda");
  const sel = form.querySelector(".sel-id-perda");
  if (!chk || !campo || !sel) return;
  const convertido = chk.checked;
  campo.style.display = convertido ? "none" : "flex";
  sel.required = !convertido;
  if (convertido) sel.value = "";
}

window.atualizarCampoPerda = atualizarCampoPerda;

document.querySelectorAll(".form-venda").forEach((form) => {
  const chk = form.querySelector(".chk-convertido");
  if (chk) {
    chk.addEventListener("change", () => atualizarCampoPerda(form));
    atualizarCampoPerda(form);
  }
  form.addEventListener("submit", (e) => {
    const chkEl = form.querySelector(".chk-convertido");
    const sel = form.querySelector(".sel-id-perda");
    if (chkEl && !chkEl.checked && sel && !sel.value) {
      e.preventDefault();
      alert("Venda sem conversão deve vincular o ID da tratativa — o impacto vem sempre do problema registrado.");
      sel.focus();
    }
  });
});
