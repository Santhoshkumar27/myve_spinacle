

import React, { useState } from "react";

const FIMcpLogin = ({ sessionId }) => {
  const [mobile, setMobile] = useState("");
  const [otp, setOtp] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleLogin = () => {
    if (!mobile) {
      alert("Enter mobile number");
      return;
    }

    const url = `http://localhost:8080/mockWebPage?sessionId=${sessionId}`;
    window.open(url, "_blank");
    setSubmitted(true);
  };

  return (
    <div className="border p-4 rounded-md bg-card w-full max-w-sm mx-auto mt-6">
      <h2 className="text-xl font-semibold mb-2">Fi MCP Login</h2>
      <p className="text-sm text-muted-foreground mb-4">
        Enter your registered mobile number and authenticate to continue.
      </p>
      <div className="space-y-3">
        <input
          type="text"
          placeholder="Mobile Number"
          value={mobile}
          onChange={(e) => setMobile(e.target.value)}
          className="w-full px-3 py-2 border border-border rounded-md"
        />
        <button
          onClick={handleLogin}
          className="w-full py-2 bg-primary text-white rounded-md"
        >
          Authenticate
        </button>
        {submitted && (
          <div className="text-green-600 text-sm mt-2">
            Login page opened in new tab. Enter number and any OTP.
          </div>
        )}
      </div>
    </div>
  );
};

export default FIMcpLogin;