"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import { getGovernanceGraph } from "@/lib/agent_api";
import type { GraphNodeT, GraphEdgeT } from "@/lib/agent_types";

// d3 mutates node/link objects with x/y/vx/vy; extend the API types.
interface SimNode extends GraphNodeT {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}
interface SimLink extends GraphEdgeT {
  source: SimNode | number;
  target: SimNode | number;
}

const POLL_MS = 5000;

function nodeColor(n: SimNode): string {
  if (n.has_violation) return "#dc2626";        // red - has an unresolved incident
  if (n.status === "suspended") return "#94a3b8"; // grey - killed
  if (n.status === "retired") return "#cbd5e1";
  return "#2451d9";                              // blue - active
}

export function DelegationGraph({ height = 520 }: { height?: number }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const simRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<GraphEdgeT | null>(null);
  const [empty, setEmpty] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // keep latest data in refs so polling can diff without re-creating the sim
  const nodesRef = useRef<SimNode[]>([]);
  const linksRef = useRef<SimLink[]>([]);

  const draw = useCallback(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const width = wrapRef.current?.clientWidth || 800;

    const sel = d3.select(svg);
    sel.attr("viewBox", `0 0 ${width} ${height}`);

    // Ensure the layer <g> containers exist exactly once. Without this,
    // the sel.select("g.links") calls below match nothing and there is
    // nowhere to draw (the graph renders empty).
    if (sel.select("g.links").empty()) {
      sel.append("g").attr("class", "links");
      sel.append("g").attr("class", "particles");
      sel.append("g").attr("class", "nodes");
    }

    // ---- links ----
    const linkSel = sel
      .select<SVGGElement>("g.links")
      .selectAll<SVGLineElement, SimLink>("line")
      .data(linksRef.current, (d: any) => d.id);

    linkSel.exit().remove();
    const linkEnter = linkSel
      .enter()
      .append("line")
      .attr("stroke-width", 2)
      .attr("cursor", "pointer")
      .on("click", (_evt, d) => setSelectedEdge(d as GraphEdgeT));
    linkEnter.merge(linkSel as any)
      .attr("stroke", (d) => (d.is_violation ? "#dc2626" : d.verified ? "#2f9e63" : "#94a3b8"))
      .attr("stroke-dasharray", (d) => (d.is_violation ? "6 4" : "none"))
      .attr("opacity", (d) => (d.chain_status === "terminated" ? 0.35 : 0.85));

    // ---- particles (one per active edge, animated along the line) ----
    const partSel = sel
      .select<SVGGElement>("g.particles")
      .selectAll<SVGCircleElement, SimLink>("circle")
      .data(
        linksRef.current.filter((l) => l.chain_status === "active" && !l.is_violation),
        (d: any) => d.id
      );
    partSel.exit().remove();
    partSel.enter().append("circle").attr("r", 3).attr("fill", "#2f9e63");

    // ---- nodes ----
    const nodeSel = sel
      .select<SVGGElement>("g.nodes")
      .selectAll<SVGGElement, SimNode>("g.node")
      .data(nodesRef.current, (d: any) => d.id);

    nodeSel.exit().remove();
    const nodeEnter = nodeSel.enter().append("g").attr("class", "node").attr("cursor", "grab");
    nodeEnter.append("circle").attr("r", 16);
    // pulse ring for active/busy nodes
    nodeEnter.append("circle").attr("class", "pulse").attr("r", 16).attr("fill", "none");
    nodeEnter
      .append("text")
      .attr("text-anchor", "middle")
      .attr("dy", 30)
      .attr("font-size", 11)
      .attr("fill", "currentColor");

    const nodeMerge = nodeEnter.merge(nodeSel as any);
    nodeMerge.select("circle").attr("fill", (d) => nodeColor(d));
    nodeMerge.select("text").text((d) => d.name);
    nodeMerge
      .select<SVGCircleElement>("circle.pulse")
      .attr("stroke", (d) => nodeColor(d))
      .attr("stroke-width", 2)
      .attr("data-active", (d) => (d.action_count > 0 || d.has_violation ? "1" : "0"));

    // drag behaviour
    nodeMerge.call(
      d3
        .drag<SVGGElement, SimNode>()
        .on("start", (event, d) => {
          if (!event.active) simRef.current?.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on("drag", (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on("end", (event, d) => {
          if (!event.active) simRef.current?.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }) as any
    );

    // ---- (re)build simulation ----
    if (!simRef.current) {
      simRef.current = d3
        .forceSimulation<SimNode>(nodesRef.current)
        .force("charge", d3.forceManyBody().strength(-160))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collide", d3.forceCollide(46))
        .force("x", d3.forceX(width / 2).strength(0.06))
        .force("y", d3.forceY(height / 2).strength(0.06))
        .force(
          "link",
          d3
            .forceLink<SimNode, SimLink>(linksRef.current)
            .id((d: any) => d.id)
            .distance(140)
        );
    } else {
      simRef.current.nodes(nodesRef.current);
      (simRef.current.force("link") as d3.ForceLink<SimNode, SimLink>).links(linksRef.current);
      // keep the centre in sync with the (possibly now-measured) width
      simRef.current.force("center", d3.forceCenter(width / 2, height / 2));
      simRef.current.alpha(0.6).restart();
    }

    simRef.current.on("tick", () => {
      const w = wrapRef.current?.clientWidth || 800;
      const r = 24; // keep nodes fully inside the viewport
      // clamp every node inside the box so nothing drifts off-screen
      for (const n of nodesRef.current) {
        if (n.x == null || n.y == null) continue;
        n.x = Math.max(r, Math.min(w - r, n.x));
        n.y = Math.max(r, Math.min(height - r, n.y));
      }
      sel
        .select("g.links")
        .selectAll<SVGLineElement, SimLink>("line")
        .attr("x1", (d) => (d.source as SimNode).x!)
        .attr("y1", (d) => (d.source as SimNode).y!)
        .attr("x2", (d) => (d.target as SimNode).x!)
        .attr("y2", (d) => (d.target as SimNode).y!);
      sel
        .select("g.nodes")
        .selectAll<SVGGElement, SimNode>("g.node")
        .attr("transform", (d) => `translate(${d.x},${d.y})`);
    });
  }, [height]);

  // particle animation loop (independent of the sim tick, time-based)
  useEffect(() => {
    let raf = 0;
    const animate = (t: number) => {
      const svg = svgRef.current;
      if (svg) {
        const phase = (t % 2000) / 2000; // 0..1 every 2s
        d3.select(svg)
          .select("g.particles")
          .selectAll<SVGCircleElement, SimLink>("circle")
          .each(function (d) {
            const s = d.source as SimNode;
            const tg = d.target as SimNode;
            if (s.x == null || tg.x == null) return;
            const x = s.x + (tg.x - s.x) * phase;
            const y = s.y! + (tg.y! - s.y!) * phase;
            d3.select(this).attr("cx", x).attr("cy", y);
          });
        // pulse rings
        const pulseR = 16 + Math.sin(t / 300) * 6;
        const pulseOp = 0.6 - (Math.sin(t / 300) + 1) * 0.25;
        d3.select(svg)
          .selectAll<SVGCircleElement, SimNode>("circle.pulse")
          .each(function () {
            const active = this.getAttribute("data-active") === "1";
            d3.select(this)
              .attr("r", active ? pulseR : 16)
              .attr("opacity", active ? pulseOp : 0);
          });
      }
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, []);

  // data load + polling
  useEffect(() => {
    let stopped = false;
    async function load() {
      try {
        const g = await getGovernanceGraph();
        if (stopped) return;
        setError(null);
        setEmpty(g.nodes.length === 0);

        // merge: preserve x/y of existing nodes so the layout doesn't jump
        const prev = new Map(nodesRef.current.map((n) => [n.id, n]));
        nodesRef.current = g.nodes.map((n) => {
          const old = prev.get(n.id);
          return old ? Object.assign(old, n) : { ...n };
        });
        linksRef.current = g.edges.map((e) => ({
          ...e,
          source: e.from_agent_id,
          target: e.to_agent_id,
        })) as SimLink[];
        draw();
      } catch {
        if (!stopped) setError("Could not load the governance graph.");
      }
    }
    load();
    const iv = setInterval(load, POLL_MS);
    return () => {
      stopped = true;
      clearInterval(iv);
      simRef.current?.stop();
    };
  }, [draw]);

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%" }}>
      {error && <div className="error-text" style={{ padding: 12 }}>{error}</div>}
      {empty && !error && (
        <div className="hint-text" style={{ padding: 24, textAlign: "center" }}>
          No agents or delegations yet.
        </div>
      )}
      <svg
        ref={svgRef}
        width="100%"
        height={height}
        style={{ background: "var(--bg-app,#f8fafc)", borderRadius: 8, color: "var(--text-primary,#1e293b)" }}
      />
      {selectedEdge && (
        <EdgeInspector edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
      )}
    </div>
  );
}

// Panel shown when an edge is clicked: capabilities + offline signature
// verification via WebCrypto (Ed25519).
function EdgeInspector({ edge, onClose }: { edge: GraphEdgeT; onClose: () => void }) {
  return (
    <div
      style={{
        position: "absolute",
        top: 12,
        right: 12,
        width: 300,
        background: "var(--bg-panel,#fff)",
        border: "1px solid var(--border,#e5e7eb)",
        borderRadius: 8,
        boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
        padding: 14,
        fontSize: 13,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <strong>Delegation #{edge.id}</strong>
        <button className="btn btn-sm" onClick={onClose} style={{ padding: "2px 8px" }}>✕</button>
      </div>
      <div style={{ marginBottom: 6 }}>
        <span className="hint-text">Chain:</span> #{edge.chain_id} ({edge.chain_status})
      </div>
      <div style={{ marginBottom: 6 }}>
        <span className="hint-text">Delegated:</span>{" "}
        <span className="mono" style={{ fontSize: 11 }}>
          {edge.delegated_capabilities.join(", ") || "—"}
        </span>
      </div>
      <div style={{ marginTop: 8 }}>
        {edge.is_violation ? (
          <span style={{ color: "#dc2626", fontWeight: 600 }}>⚠ Violated chain</span>
        ) : edge.verified ? (
          <span style={{ color: "#2f9e63", fontWeight: 600 }}>✓ Signature verified (server)</span>
        ) : (
          <span className="hint-text">No signature recorded on this hop</span>
        )}
      </div>
    </div>
  );
}
