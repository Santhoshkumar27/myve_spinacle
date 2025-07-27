

import React from 'react';

const GraphViewer = ({ graphs }) => {
  if (!graphs || graphs.length === 0) return null;

  return (
    <div className="graph-viewer">
      <h3 className="text-lg font-semibold mb-2">Visual Plan Insights</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {graphs.map((graph, idx) => (
          <div key={idx} className="border rounded shadow-sm p-2">
            <img
              src={`data:image/png;base64,${graph}`}
              alt={`Plan Chart ${idx + 1}`}
              className="w-full h-auto"
            />
          </div>
        ))}
      </div>
    </div>
  );
};

export default GraphViewer;