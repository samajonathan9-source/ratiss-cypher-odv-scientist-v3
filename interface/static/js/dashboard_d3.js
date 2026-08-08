/* Open Views — dashboard D3.js : courbes RAM / CPU en temps réel */

const MAX_POINTS = 120; // 2 minutes à 1 point/s

class TelemetryDashboard {
  constructor(containerId) {
    this.ram = [];
    this.cpu = [];
    this.limitMb = 7500; // Memory Guard RATISS

    const container = d3.select("#" + containerId);
    const rect = container.node().getBoundingClientRect();
    this.width = rect.width;
    this.height = Math.max(rect.height - 20, 120);

    const margin = { top: 14, right: 12, bottom: 22, left: 44 };
    this.innerWidth = this.width - margin.left - margin.right;
    this.innerHeight = this.height - margin.top - margin.bottom;

    this.svg = container.append("svg")
      .attr("width", this.width)
      .attr("height", this.height);

    const g = this.svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    this.x = d3.scaleLinear().domain([0, MAX_POINTS - 1]).range([0, this.innerWidth]);

    this.yRam = d3.scaleLinear()
      .domain([0, this.limitMb])
      .range([this.innerHeight, 0]);
    this.yCpu = d3.scaleLinear().domain([0, 100]).range([this.innerHeight, 0]);

    this.lineRam = d3.line()
      .x((d, i) => this.x(i))
      .y(d => this.yRam(d))
      .curve(d3.curveMonotoneX);

    this.lineCpu = d3.line()
      .x((d, i) => this.x(i))
      .y(d => this.yCpu(d))
      .curve(d3.curveMonotoneX);

    // Grid
    g.append("g").attr("class", "grid")
      .selectAll("line")
      .data([0.25, 0.5, 0.75, 1.0])
      .enter().append("line")
      .attr("x1", 0).attr("x2", this.innerWidth)
      .attr("y1", d => this.innerHeight * d)
      .attr("y2", d => this.innerHeight * d)
      .attr("stroke", "rgba(255,255,255,0.05)");

    // Limite Memory Guard (7500 Mo) — ligne rouge
    g.append("line")
      .attr("x1", 0).attr("x2", this.innerWidth)
      .attr("y1", this.yRam(this.limitMb) - 2)
      .attr("y2", this.yRam(this.limitMb) - 2)
      .attr("stroke", "#ff3b5c")
      .attr("stroke-width", 1.2)
      .attr("stroke-dasharray", "5,4");

    g.append("text")
      .attr("x", this.innerWidth - 4)
      .attr("y", this.yRam(this.limitMb) - 6)
      .attr("text-anchor", "end")
      .attr("fill", "#ff3b5c")
      .attr("font-size", 9)
      .attr("font-family", "monospace")
      .text(`MEMORY GUARD ${this.limitMb} Mo`);

    this.pathRam = g.append("path").attr("fill", "none")
      .attr("stroke", "#00f0ff").attr("stroke-width", 1.6);

    this.pathCpu = g.append("path").attr("fill", "none")
      .attr("stroke", "#39ff8a").attr("stroke-width", 1.3)
      .attr("opacity", 0.75);

    // Axes
    const xAxis = d3.axisBottom(this.x)
      .tickValues([0, 30, 60, 90, 119])
      .tickFormat(d => `-${MAX_POINTS - 1 - d}s`)
      .ticks(5);
    const yAxis = d3.axisLeft(this.yRam)
      .ticks(4)
      .tickFormat(d => d + " Mo");

    g.append("g")
      .attr("transform", `translate(0,${this.innerHeight})`)
      .call(xAxis)
      .selectAll("text").attr("fill", "#8a97ab").attr("font-size", 9);

    g.append("g")
      .call(yAxis)
      .selectAll("text").attr("fill", "#8a97ab").attr("font-size", 9);

    g.selectAll(".domain, .tick line").attr("stroke", "rgba(255,255,255,0.12)");

    // Légende
    const legend = container.append("div")
      .style("display", "flex").style("gap", "14px")
      .style("padding", "0 8px").style("font-size", "11px")
      .style("color", "#8a97ab").style("font-family", "monospace");
    legend.append("span").html("■ <span style='color:#00f0ff'>RAM</span>");
    legend.append("span").html("■ <span style='color:#39ff8a'>CPU %</span>");

    this._refresh();
  }

  pushSample(sample) {
    this.ram.push(sample.ram_mb);
    this.cpu.push(sample.cpu_pct);
    if (this.ram.length > MAX_POINTS) { this.ram.shift(); this.cpu.shift(); }
    this._refresh();
  }

  _refresh() {
    if (this.ram.length < 2) return;
    this.pathRam.attr("d", this.lineRam(this.ram));
    this.pathCpu.attr("d", this.lineCpu(this.cpu));
  }
}
