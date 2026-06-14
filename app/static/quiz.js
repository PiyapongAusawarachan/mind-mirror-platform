// Per-question modality switching on the quiz page.
// Only the active mode's input is enabled so the right value/file is submitted.
document.querySelectorAll(".answer-modes").forEach((group) => {
  const tabs = group.querySelectorAll(".tab");
  const modalityInput = group.querySelector(".modality-input");
  const inputs = group.querySelectorAll(".mode-input");

  function activate(mode) {
    modalityInput.value = mode;
    inputs.forEach((el) => {
      const on = el.dataset.mode === mode;
      el.classList.toggle("hidden", !on);
      el.disabled = !on; // disabled inputs are not submitted (avoids duplicate file_ names)
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activate(tab.dataset.mode);
    });
  });

  activate("typing");
});
