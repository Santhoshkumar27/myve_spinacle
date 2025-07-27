import React, { createContext, useContext, useState, useEffect } from 'react';

const McpContext = createContext();

export const McpProvider = ({ children }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);

  const [mfTransactions, setMfTransactions] = useState([]);
  const [bankTransactions, setBankTransactions] = useState([]);
  const [epf, setEpf] = useState(null);
  const [stocks, setStocks] = useState([]);

  // New state hooks for analytics/summaries
  const [mfAnalytics, setMfAnalytics] = useState([]);
  const [finalSnapshot, setFinalSnapshot] = useState(null);
  const [bankSummary, setBankSummary] = useState(null);
  const [investmentSummary, setInvestmentSummary] = useState(null);
  const [stockSummary, setStockSummary] = useState(null);

  const [isConnected, setIsConnected] = useState(false);
  const [tools, setTools] = useState([]);

  const [isModalOpen, setModalOpen] = useState(false);
  const openModal = () => setModalOpen(true);
  const closeModal = () => setModalOpen(false);

  const [netWorth, setNetWorth] = useState(null);
  const [assets, setAssets] = useState([]);
  const [creditSummary, setCreditSummary] = useState(null);
  const [creditReport, setCreditReport] = useState(null);

  const [monthlyTrend, setMonthlyTrend] = useState([]);
  const [accounts, setAccounts] = useState({});

  const [mobileNumber, setMobileNumber] = useState("");

  const fetchMcpData = async () => {
    setIsLoading(true);
    setIsError(false);
    try {
      // Only fetch from /api/mcp/full_snapshot and use final_snapshot exclusively
      const netRes = await fetch("/api/mcp/full_snapshot", { credentials: "include" });
      const netText = await netRes.text();
      const netData = netText ? JSON.parse(netText) : {};
      console.log("[DEBUG] FullSnapshot:", netData);

      // Use only final_snapshot for all dashboard data
      const data = netData?.data;
      const finalSnapshot = data;
      setFinalSnapshot(finalSnapshot || null);

      if (finalSnapshot && typeof finalSnapshot === "object") {
        // Net Worth
        setNetWorth(finalSnapshot?.networth?.netWorth || null);
        // Accounts
        setAccounts(finalSnapshot?.networth?.accounts || {});
        // Assets
        setAssets(Array.isArray(finalSnapshot?.assets) ? finalSnapshot.assets : []);
        // Credit Summary
        setCreditSummary(finalSnapshot?.credit_summary?.summary || null);
        // Credit Report (use only from final_snapshot.credit?.[0])
        setCreditReport(finalSnapshot?.credit?.[0] || null);
        // Monthly Trend
        setMonthlyTrend(Array.isArray(finalSnapshot?.monthly) ? finalSnapshot.monthly : []);
        // MF Transactions
        setMfTransactions(Array.isArray(finalSnapshot?.mf) ? finalSnapshot.mf : []);
        // Bank Transactions
        setBankTransactions(Array.isArray(finalSnapshot?.bank) ? finalSnapshot.bank : []);
        // EPF
        setEpf(finalSnapshot?.epf_summary || null);
        // Stocks
        setStocks(Array.isArray(finalSnapshot?.stock) ? finalSnapshot.stock : []);
        // MF Analytics
        setMfAnalytics(Array.isArray(finalSnapshot?.mfAnalytics) ? finalSnapshot.mfAnalytics : []);
        // Investment Summary
        setInvestmentSummary(finalSnapshot?.investment_summary || null);
        // Bank Summary
        setBankSummary(finalSnapshot?.bank_summary || null);
        // Stock Summary
        setStockSummary(finalSnapshot?.stock_summary || null);
      } else {
        // If no valid final_snapshot, clear all
        setNetWorth(null);
        setAccounts({});
        setAssets([]);
        setCreditSummary(null);
        setCreditReport(null);
        setMonthlyTrend([]);
        setMfTransactions([]);
        setBankTransactions([]);
        setEpf(null);
        setStocks([]);
        setMfAnalytics([]);
        setInvestmentSummary(null);
        setBankSummary(null);
        setStockSummary(null);
      }

      // Fetch profile for mobile number
      const profileRes = await fetch("/api/mcp/profile", { credentials: "include" });
      const profileData = await profileRes.json();
      console.log("[DEBUG] Profile:", profileData);
      setMobileNumber(profileData?.mobile ?? "");

      setIsLoading(false);
    } catch (err) {
      console.error("MCP data fetch failed", err);
      setIsError(true);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    setIsConnected(true); // Force connection for data fetch
    fetchMcpData(); // Call once on mount
  }, []);

  return (
    <McpContext.Provider value={{
      isConnected, setIsConnected,
      tools, setTools,
      isModalOpen, openModal, closeModal,
      netWorth, setNetWorth,
      assets, setAssets,
      creditSummary, setCreditSummary,
      creditReport, setCreditReport,
      monthlyTrend, setMonthlyTrend,
      accounts, setAccounts,
      mobileNumber, setMobileNumber,
      mfTransactions, setMfTransactions,
      bankTransactions, setBankTransactions,
      epf, setEpf,
      stocks, setStocks,
      // New context fields
      mfAnalytics, setMfAnalytics,
      finalSnapshot, setFinalSnapshot,
      bankSummary, setBankSummary,
      investmentSummary, setInvestmentSummary,
      stockSummary, setStockSummary,
      fetchMcpData,
      refreshMcp: fetchMcpData,
      isLoading,
      isError
    }}>
      {children}
    </McpContext.Provider>
  );
};

export const useMcp = () => {
  const context = useContext(McpContext);
  if (!context) {
    throw new Error('useMcp must be used within a McpProvider');
  }
  return context;
};

export { McpContext };
