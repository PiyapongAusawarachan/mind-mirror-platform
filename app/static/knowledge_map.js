// Render the knowledge map (Cytoscape) and the understanding pie (Chart.js).
(function () {
  const dataEl = document.getElementById("map-data");
  if (!dataEl) return;
  const data = JSON.parse(dataEl.textContent);

  const elements = [];
  data.nodes.forEach((n) => {
    elements.push({ data: { id: n.id, label: n.id, detail: n.detail, color: data.colors[n.level] } });
  });
  data.edges.forEach((e) => {
    elements.push({ data: { source: e.source, target: e.target, label: e.relation } });
  });

  if (document.getElementById("cy") && window.cytoscape) {
    cytoscape({
      container: document.getElementById("cy"),
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            color: "#0f172a",
            "font-size": "11px",
            "font-family": "Inter, 'Noto Sans Thai', sans-serif",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "90px",
            width: "label",
            height: "label",
            padding: "12px",
            shape: "round-rectangle",
          },
        },
        {
          selector: "edge",
          style: {
            label: "data(label)",
            "font-size": "9px",
            color: "#94a3b8",
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "line-color": "#cbd5e1",
            "target-arrow-color": "#cbd5e1",
            width: 1.5,
          },
        },
      ],
      layout: { name: "cose", animate: false, padding: 24 },
    });
  }

  const pieEl = document.getElementById("pie");
  if (pieEl && window.Chart) {
    const keys = Object.keys(data.distribution);
    new Chart(pieEl, {
      type: "doughnut",
      data: {
        labels: keys.map((k) => data.labels[k]),
        datasets: [{ data: keys.map((k) => data.distribution[k]), backgroundColor: keys.map((k) => data.colors[k]) }],
      },
      options: { plugins: { legend: { position: "bottom" } } },
    });
  }
})();
