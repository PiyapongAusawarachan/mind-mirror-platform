// Render mastery-over-time line charts (student lesson + teacher views).
(function () {
  if (!window.Chart) return;
  const pairs = [
    ["timeline", "timeline-data"],
    ["course-timeline", "course-timeline-data"],
  ];
  pairs.forEach(([canvasId, dataId]) => {
    const canvas = document.getElementById(canvasId);
    const dataEl = document.getElementById(dataId);
    if (!canvas || !dataEl) return;
    const data = JSON.parse(dataEl.textContent);
    const points = data.points || [];
    new Chart(canvas, {
      type: "line",
      data: {
        labels: points.map((p) => p.date),
        datasets: [
          {
            label: data.label,
            data: points.map((p) => p.mastery),
            borderColor: "#6366f1",
            backgroundColor: "rgba(99,102,241,0.15)",
            fill: true,
            tension: 0.3,
            pointRadius: 4,
          },
        ],
      },
      options: {
        scales: { y: { min: 0, max: 100, ticks: { callback: (v) => v + "%" } } },
        plugins: { legend: { position: "bottom" } },
      },
    });
  });
})();
