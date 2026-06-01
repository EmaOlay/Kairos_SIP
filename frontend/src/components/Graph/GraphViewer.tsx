import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import styles from './GraphViewer.module.css';

interface GraphViewerProps {
  data: {
    nodes: any[];
    edges: any[];
  };
}

const GraphViewer: React.FC<GraphViewerProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;

    const nodes = new DataSet(data.nodes.map(node => ({
      ...node,
      level: node.year,
      font: { color: '#f0f6fc', face: 'Inter', size: 13 },
      shape: 'box',
      margin: 10,
      widthConstraint: { maximum: 160 },
      borderWidth: 2,
      shadow: true
    })));

    const edges = new DataSet(data.edges.map(edge => ({
      ...edge,
      color: { color: '#8b949e', highlight: '#00f2ff' },
      width: 2,
      arrows: { to: { enabled: true, scaleFactor: 0.5 } },
      smooth: { type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.5 }
    })));

    const options = {
      nodes: {
        color: {
          background: '#1c2128',
          border: '#30363d',
          highlight: { background: '#1c2128', border: '#00f2ff' }
        }
      },
      physics: {
        enabled: false,
      },
      layout: {
        hierarchical: {
          enabled: true,
          direction: 'LR',
          sortMethod: 'directed',
          shakeTowards: 'roots',
          levelSeparation: 280,
          nodeSpacing: 80,
          treeSpacing: 200,
          blockShifting: true,
          edgeMinimization: true,
          parentCentralization: true,
        }
      },
      interaction: {
        hover: true,
        navigationButtons: true,
        keyboard: true
      }
    };

    const network = new Network(containerRef.current, { nodes, edges }, options);

    return () => {
      network.destroy();
    };
  }, [data]);

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Mapa de Correlatividades</h3>
      <div ref={containerRef} className={styles.network} />
    </div>
  );
};

export default GraphViewer;
