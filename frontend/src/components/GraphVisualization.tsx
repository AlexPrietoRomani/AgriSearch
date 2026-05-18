import { useRef, useEffect, useState } from "react";
import { Network, DataSet } from "vis-network/standalone";
import type { Options, Node, Edge } from "vis-network";
import type { GraphNode, GraphEdge } from "../lib/graph-api";

const CLUSTER_COLORS = [
  { bg: "#10b981", border: "#059669" },
  { bg: "#6366f1", border: "#4f46e5" },
  { bg: "#f59e0b", border: "#d97706" },
  { bg: "#ef4444", border: "#dc2626" },
  { bg: "#8b5cf6", border: "#7c3aed" },
  { bg: "#06b6d4", border: "#0891b2" },
  { bg: "#ec4899", border: "#db2777" },
  { bg: "#84cc16", border: "#65a30d" },
  { bg: "#f97316", border: "#ea580c" },
  { bg: "#14b8a6", border: "#0d9488" },
];

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  graphType: "citation" | "thematic";
  layout: "hierarchical" | "force" | "circular";
  onNodeSelect: (node: GraphNode | null) => void;
  selectedNodeId: string | null;
}

function getClusterColor(cluster?: number) {
  if (cluster === undefined || cluster === null) return CLUSTER_COLORS[0];
  return CLUSTER_COLORS[cluster % CLUSTER_COLORS.length];
}

export default function GraphVisualization({ nodes, edges, graphType, layout, onNodeSelect, selectedNodeId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!containerRef.current || nodes.length === 0) return;

    const visNodes = nodes.map((n) => {
      const color = n.cluster !== undefined && n.cluster !== null
        ? getClusterColor(n.cluster)
        : n.status === "cited_external"
          ? { bg: "#64748b", border: "#475569" }
          : { bg: "#10b981", border: "#059669" };

      return {
        id: n.id,
        label: n.label.length > 40 ? n.label.slice(0, 37) + "..." : n.label,
        title: n.title,
        color: {
          background: n.color?.background || color.bg,
          border: n.color?.border || color.border,
          highlight: { background: color.bg, border: "#ffffff" },
          hover: { background: color.bg, border: "#94a3b8" },
        },
        size: n.size || (n.status === "cited_external" ? 10 : 15),
        shape: n.shape || "dot",
        font: { color: "#e2e8f0", size: 12, face: "Inter, sans-serif" },
        borderWidth: 2,
        shadow: true,
      } as Node;
    });

    const visEdges = edges.map((e) => ({
      id: `${e.from}-${e.to}`,
      from: e.from,
      to: e.to,
      arrows: graphType === "citation" ? { to: { enabled: true, scaleFactor: 0.5 } } : undefined,
      color: {
        color: e.color?.color || (graphType === "citation" ? "#475569" : "#334155"),
        highlight: "#10b981",
        hover: "#64748b",
      },
      width: e.width || (graphType === "thematic" && e.cosine_similarity ? e.cosine_similarity * 3 : 1),
      dashes: graphType === "citation" ? false : (e.dashes || false),
      smooth: { type: "continuous", roundness: 0.2 },
      font: { color: "#94a3b8", size: 10, align: "top" },
      title: e.cosine_similarity ? `Similarity: ${e.cosine_similarity.toFixed(3)}` : undefined,
    })) as Edge[];

    const nodeDataSet = new DataSet(visNodes);
    const edgeDataSet = new DataSet(visEdges);

    const options: Options = {
      physics: {
        enabled: layout === "force",
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 100,
          springConstant: 0.05,
          damping: 0.4,
        },
        stabilization: { iterations: 150, fit: true },
      },
      layout: {
        improvedLayout: true,
      },
      interaction: {
        hover: true,
        tooltipDelay: 100,
        zoomView: true,
        dragView: true,
        dragNodes: true,
      },
      edges: {
        smooth: { enabled: true, type: "continuous" },
      },
    };

    if (layout === "hierarchical") {
      options.layout = {
        hierarchical: {
          enabled: true,
          direction: "UD",
          sortMethod: "hubsize",
          levelSeparation: 120,
          nodeSpacing: 100,
        },
      };
      options.physics = { enabled: false };
    } else if (layout === "circular") {
      options.physics = { enabled: false };
    }

    const network = new Network(containerRef.current, { nodes: nodeDataSet, edges: edgeDataSet }, options);
    networkRef.current = network;

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n) => n.id === nodeId);
        if (node) onNodeSelect(node);
      } else {
        onNodeSelect(null);
      }
    });

    network.on("doubleClick", (params) => {
      if (params.nodes.length > 0) {
        network.focus(params.nodes[0] as string, {
          scale: 1.5,
          animation: { duration: 300, easingFunction: "easeInOutQuad" },
        });
      }
    });

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges, graphType, layout]);

  useEffect(() => {
    if (!networkRef.current || !selectedNodeId) return;
    networkRef.current.selectNodes([selectedNodeId], true);
    networkRef.current.focus(selectedNodeId, {
      scale: 1.3,
      animation: { duration: 300, easingFunction: "easeInOutQuad" },
    });
  }, [selectedNodeId]);

  return (
    <div
      ref={containerRef}
      className="w-full bg-slate-900/40 rounded-2xl border border-slate-800 overflow-hidden"
      style={{ height: dimensions.width > 768 ? "600px" : "400px" }}
    />
  );
}
