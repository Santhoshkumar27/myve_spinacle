import React, { useEffect, useState } from "react";

const DataSim = () => {
  const [scenarios, setScenarios] = useState({});

  useEffect(() => {
    const mobile = localStorage.getItem("user_mobile");
    fetch("/api/ai/data_agent/scenarios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user: mobile })
    })
      .then((res) => res.json())
      .then(setScenarios)
      .catch((err) => console.error("Failed to fetch scenarios:", err));
  }, []);

  if (!Object.keys(scenarios).length) return <div>Loading scenarios...</div>;

  // Determine max numeric value for scaling bars
  const allValues = [];
  Object.values(scenarios).forEach((value) => {
    if (typeof value === "object" && value !== null) {
      Object.values(value).forEach((v) => {
        if (typeof v === "number") allValues.push(v);
      });
    }
  });
  const maxValue = Math.max(...allValues, 1);

  return (
    <div style={{ padding: "20px" }}>
      <h2>Financial Simulator Scenarios</h2>
      <div style={{ marginTop: "20px" }}>
        {Object.entries(scenarios).map(([key, value]) => (
          <div
            key={key}
            style={{
              marginBottom: "30px",
              border: "1px solid #ccc",
              borderRadius: "8px",
              padding: "15px",
              backgroundColor: "#f9f9f9",
            }}
          >
            <h3 style={{ textTransform: "capitalize" }}>{key.replace(/_/g, " ")}</h3>
            {typeof value === "object" && value !== null ? (
              <dl style={{ margin: 0 }}>
                {Object.entries(value).map(([subKey, subValue]) => {
                  const label = subKey
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase());
                  const isNumber = typeof subValue === "number";
                  return (
                    <React.Fragment key={subKey}>
                      <dt
                        style={{
                          fontWeight: "bold",
                          marginTop: "10px",
                          marginBottom: "4px",
                        }}
                      >
                        {label}
                      </dt>
                      <dd
                        style={{
                          margin: 0,
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        <span>
                          {isNumber
                            ? `₹${subValue.toLocaleString()}`
                            : subValue === true
                            ? "Yes"
                            : subValue === false
                            ? "No"
                            : subValue}
                        </span>
                        {isNumber && (
                          <div
                            style={{
                              height: "12px",
                              backgroundColor: "#4caf50",
                              width: `${(subValue / maxValue) * 100}%`,
                              borderRadius: "6px",
                              flexShrink: 0,
                            }}
                          />
                        )}
                      </dd>
                    </React.Fragment>
                  );
                })}
              </dl>
            ) : (
              <p>Error: {value}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default DataSim;