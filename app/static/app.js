// Tab switching for the explanation input (type / write / speak) on lesson page.
document.querySelectorAll(".panel > .tabs").forEach((tabs) => {
  const section = tabs.parentElement;
  const buttons = tabs.querySelectorAll(".tab");
  const panels = section.querySelectorAll(".tab-panel");
  buttons.forEach((btn) => {
    btn.addEventListener("click", () => {
      buttons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      panels.forEach((p) => p.classList.toggle("hidden", p.dataset.panel !== btn.dataset.tab));
    });
  });
});
