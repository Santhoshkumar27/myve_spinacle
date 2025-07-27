import React, { useState, useContext } from "react";
import { McpContext } from "../context/McpContext";

const McpLoginModal = ({ onClose, onSuccess }) => {
  const [phoneNumber, setPhoneNumber] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const { setMobileNumber, fetchMcpData } = useContext(McpContext);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const res = await fetch("http://localhost:5050/api/mcp/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          phoneNumber,
          otp
        }),
        credentials: "include"
      });

      if (res.ok) {
        const connectRes = await fetch("http://localhost:5050/api/mcp/connect", {
          method: "GET",
          credentials: "include"
        });
        if (connectRes.ok) {
          setMobileNumber(phoneNumber);
          await fetchMcpData(); // Fetch updated data
          if (onSuccess) onSuccess(phoneNumber);
          onClose();
        } else {
          setError("MCP connection failed after login.");
        }
      } else {
        setError("Login failed. Please check your OTP or try again.");
      }
    } catch (err) {
      setError("Server error. Try again.");
    }
  };

  return (
    <div style={{
      position: "fixed", top: 0, left: 0, width: "100%", height: "100%",
      backgroundColor: "rgba(0,0,0,0.5)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 9999
    }}>
      <div style={{
        backgroundColor: "#2d2d2d", color: "#fff", padding: "2rem",
        borderRadius: "1rem", width: "90%", maxWidth: "400px"
      }}>
        <h2 style={{ color: "#20d4aa" }}>Fi MCP Login</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ margin: "1rem 0" }}>
            <label>Phone Number</label>
            <input
              style={{ width: "100%", padding: "0.5rem", marginTop: "0.3rem", borderRadius: "0.5rem" }}
              type="text"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
            />
          </div>
          <div style={{ margin: "1rem 0" }}>
            <label>OTP</label>
            <input
              style={{ width: "100%", padding: "0.5rem", marginTop: "0.3rem", borderRadius: "0.5rem" }}
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              required
            />
          </div>
          {error && <div style={{ color: "#ff4d4f", marginBottom: "1rem" }}>{error}</div>}
          <button type="submit" style={{
            backgroundColor: "#20d4aa", border: "none", padding: "0.75rem",
            width: "100%", borderRadius: "0.5rem", color: "#fff", fontWeight: "bold"
          }}>
            Submit
          </button>
          <button type="button" onClick={onClose} style={{
            marginTop: "0.5rem", width: "100%", background: "none",
            border: "1px solid #888", color: "#ccc", padding: "0.5rem", borderRadius: "0.5rem"
          }}>
            Cancel
          </button>
        </form>
      </div>
    </div>
  );
};

export default McpLoginModal;
