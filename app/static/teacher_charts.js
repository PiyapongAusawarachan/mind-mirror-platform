// Render one pie per topic for the teacher's overall understanding view.
(function () {
  const dataEl = document.getElementById("pie-data");
  const grid = document.getElementById("overall-pies");
  if (!dataEl || !grid || !window.Chart) return;
  const data = JSON.parse(dataEl.textContent);
  const levels = Object.keys(data.colors);

  Object.entries(data.topics).forEach(([topic, dist]) => {
    const wrap = document.createElement("div");
    wrap.className = "pie-cell";
    const h = document.createElement("h4");
    h.textContent = topic;
    const canvas = document.createElement("canvas");
    wrap.appendChild(h);
    wrap.appendChild(canvas);
    grid.appendChild(wrap);

    new Chart(canvas, {
      type: "pie",
      data: {
        labels: levels.map((l) => data.labels[l]),
        datasets: [{ data: levels.map((l) => dist[l] || 0), backgroundColor: levels.map((l) => data.colors[l]) }],
      },
      options: { plugins: { legend: { display: false } } },
    });
  });
})();
