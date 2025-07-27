import React, { useState } from 'react';
import { useEffect } from 'react';
import { useMcp } from '../context/McpContext';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { DollarSign, TrendingUp, Shield, Activity, Upload, MessageCircle, Target, BarChart3, Bell } from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend, AreaChart, Area, CartesianGrid, XAxis, YAxis, LineChart, Line } from 'recharts';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { IndianRupee } from 'lucide-react';

const formatAssets = (rawAssets) => {
  const colorMap = {
    "ASSET_TYPE_MUTUAL_FUND": "#14B8A6",
    "ASSET_TYPE_EPF": "#38BDF8",
    "ASSET_TYPE_INDIAN_SECURITIES": "#F97316",
    "ASSET_TYPE_SAVINGS_ACCOUNTS": "#8B5CF6",
    "ASSET_TYPE_US_SECURITIES": "#6366F1"
  };
  return rawAssets.map(a => ({
    name: a.netWorthAttribute.replace("ASSET_TYPE_", "").replace(/_/g, " "),
    value: parseInt(a?.value?.units || "0", 10),
    color: colorMap[a.netWorthAttribute] || "#94a3b8"
  }));
};

const Dashboard = () => {
  const [showStockModal, setShowStockModal] = useState(false);
  const [showAccountModal, setShowAccountModal] = useState(false);
  const [showEpfModal, setShowEpfModal] = useState(false);
  const { finalSnapshot, creditSummary, mobileNumber, mfTransactions: mfRaw, bankTransactions: bankRaw, epf, stocks: stocksRaw, mfAnalytics, equitySummary, bankSummary, investmentSummary, stockSummary } = useMcp();

  // Use creditReport strictly from finalSnapshot, fallback to empty object
  const creditReport = finalSnapshot?.credit?.[0] ?? {};

  // Use net worth strictly from finalSnapshot
  let netWorth = null;
  const netWorthRaw = finalSnapshot?.networth?.netWorth ?? null;
  netWorth = typeof netWorthRaw?.units === "string"
    ? { ...netWorthRaw, units: parseInt(netWorthRaw.units, 10) }
    : netWorthRaw;
  // Use assets strictly from finalSnapshot
  const assets = Array.isArray(finalSnapshot?.assets) ? finalSnapshot.assets : [];
  // Use monthlyTrend strictly from finalSnapshot
  const monthlyTrend = Array.isArray(finalSnapshot?.monthly) ? finalSnapshot.monthly : [];
  // Compute monthlyCreditGrowth from monthlyTrend
  const monthlyCreditGrowth = (() => {
    if (!Array.isArray(monthlyTrend) || monthlyTrend.length === 0) return "N/A";
    const sorted = [...monthlyTrend].sort((a, b) => new Date(a.label) - new Date(b.label));
    const first = sorted[0]?.creditScore ?? 0;
    const last = sorted[sorted.length - 1]?.creditScore ?? 0;
    if (monthlyTrend.length === 1) return "+0.0%";
    const growth = first === 0 ? 0 : ((last - first) / first) * 100;
    return `${growth >= 0 ? '+' : ''}${growth.toFixed(1)}%`;
  })();
const mfTransactions = Array.isArray(mfRaw)
  ? mfRaw.flatMap((item) => {
      if (!item || !Array.isArray(item.txns)) return [];
      return item.txns.map((txn) => ({
        ...txn,
        scheme_name: item.schemeName || "Unnamed Scheme"
      }));
    })
  : [];
const bankTransactions = Array.isArray(bankRaw) ? bankRaw : [];
const safeBankTransactions = Array.isArray(bankTransactions)
  ? bankTransactions.flatMap(b =>
      Array.isArray(b.txns)
        ? b.txns.map(txn => ({
            amount: parseInt(txn?.[0] || 0),
            description: txn?.[1] || "Transaction",
            date: txn?.[2] || "Unknown Date",
            mode: txn?.[4] || "",
            balance: parseInt(txn?.[5] || 0)
          }))
        : []
    )
  : [];
  const stocks = Array.isArray(stocksRaw) ? stocksRaw : [];

  console.debug("[DEBUG] Assets:", assets);
  console.debug("[DEBUG] Credit Summary:", creditSummary);
  console.debug("[DEBUG] Credit Report:", creditReport);
  console.debug("[DEBUG] Monthly Trend:", monthlyTrend);
  console.debug("[DEBUG] Stocks:", stocks);
  console.debug("[DEBUG] MF Transactions:", mfTransactions);
  const isLoading = netWorth === null && assets === null && creditSummary === null;
  const [userId, setUserId] = useState(null);
  const [timelineData, setTimelineData] = useState([]);
  // Stable Net Worth state
  const [stableNetWorth, setStableNetWorth] = useState(null);
  // Update stableNetWorth when netWorth is valid, but prevent infinite update loop
  useEffect(() => {
    if (
      netWorth?.units &&
      typeof netWorth.units === "number" &&
      netWorth.units > 0 &&
      (!stableNetWorth || stableNetWorth.units !== netWorth.units)
    ) {
      setStableNetWorth(netWorth);
    }
  }, [netWorth, stableNetWorth]);

  // More defensive logic for extracting creditScoreRaw to avoid flickering
  const creditScoreRaw = (() => {
    const score1 = creditReport?.creditReportData?.score?.bureauScore;
    const score2 = creditSummary?.creditScore;
    const validScore1 = (typeof score1 === 'string' || typeof score1 === 'number') ? parseInt(score1, 10) : null;
    const validScore2 = typeof score2 === 'number' ? score2 : null;
    if (validScore1 && validScore1 > 0) return validScore1;
    if (validScore2 && validScore2 > 0) return validScore2;
    return null;
  })();
  // Improved parsing of creditScore
  const creditScore = creditScoreRaw !== null ? parseInt(creditScoreRaw, 10) : 0;
  // Stable Credit Score state
  const [stableCreditScore, setStableCreditScore] = useState(null);
  useEffect(() => {
    if (
      creditScore > 0 &&
      (!stableCreditScore || stableCreditScore !== creditScore)
    ) {
      setStableCreditScore(creditScore);
    }
  }, [creditScore, stableCreditScore]);

useEffect(() => {
  if (mobileNumber) setUserId(mobileNumber);
}, [mobileNumber]);



// Timeline data effect
useEffect(() => {
  if (!userId) return;
  fetch("/api/ai/data_agent/timeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt: "Show a timeline view of my recent transaction activity",
      user_id: userId
    })
  })
    .then(res => res.json())
    .then(data => setTimelineData(data.timeline || []));
}, [userId]);
  // Fallback initializations for arrays to avoid undefined errors
  const safeMfTransactions = Array.isArray(mfTransactions) ? mfTransactions : [];
  const safeStocks = Array.isArray(stocks) ? stocks : [];
  const safeMfAnalytics = Array.isArray(mfAnalytics) ? mfAnalytics : [];
  const safeEquitySummary = Array.isArray(equitySummary) ? equitySummary : [];

  // Always use accounts from finalSnapshot.networth.accounts
  const accounts = finalSnapshot?.networth?.accounts || {};

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50 text-slate-600">
        <div className="flex flex-col items-center space-y-4">
          <svg className="w-12 h-12 animate-spin text-teal-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-lg">Constructing Your Financial Overview...</p>
        </div>
      </div>
    );
  }
  const assetAllocation = Array.isArray(assets) ? formatAssets(assets) : [];
  const dailyChange = creditSummary?.dailyChange || 0;
  let creditLabel = "N/A";
  if (creditScore >= 800) creditLabel = "Excellent";
  else if (creditScore >= 700) creditLabel = "Very Good";
  else if (creditScore >= 600) creditLabel = "Good";
  else if (creditScore > 0) creditLabel = "Needs Improvement";
  // Compute riskLevel dynamically based on credit utilization and credit score
  const creditAccounts = Object.values(accounts || {}).filter(acc => acc.accountDetails?.accInstrumentType === "ACC_INSTRUMENT_TYPE_CREDIT_CARD");
  const totalCreditLimit = creditAccounts.reduce((sum, acc) => sum + parseInt(acc?.creditCardSummary?.creditLimit?.units || 0), 0);
  const totalOutstanding = creditAccounts.reduce((sum, acc) => sum + parseInt(acc?.creditCardSummary?.currentBalance?.units || 0), 0);
  const creditUtilization = totalCreditLimit > 0 ? (totalOutstanding / totalCreditLimit) * 100 : 0;
  const creditFactor = creditScore < 600 ? 50 : creditScore < 700 ? 30 : 10;
  const utilizationFactor = creditUtilization > 80 ? 30 : creditUtilization > 50 ? 20 : 10;
  const computedRiskLevel = Math.min(100, creditFactor + utilizationFactor);
  const getCreditScoreColor = (score) => {
    if (score >= 700) return "text-green-600";
    if (score >= 600) return "text-yellow-600";
    return "text-red-600";
  };
  // Handler for timeline chart point click (shared for both lines)
  const handleTimelineClick = (e, payload) => {
    if (payload && payload.payload && payload.payload.date) {
      fetch("/api/ai/data_agent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          insight_type: "timeline_point",
          date: payload.payload.date
        })
      })
        .then(res => res.json())
        .then(data => {
          if (data.text) {
            setAiSummary(data.text);
          }
        });
    }
  };
  // Handler for card click, especially for Credit Score card
  const handleCardClick = (promptText) => {
    if (!userId) return;
    fetch("/api/ai/data_agent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: promptText, user_id: userId })
    })
      .then(res => res.json())
      .then(data => {
        if (data.text) {
          setAiSummary(data.text);
        }
      });
  };

  // New fallback logic: show fallback UI but allow dashboard to render regardless
  const hasCriticalData =
    (typeof netWorth?.units === 'number' && netWorth.units > 0) ||
    (typeof creditScore === 'number' && creditScore > 0) ||
    (Array.isArray(assetAllocation) && assetAllocation.length > 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-white text-slate-800 px-4 sm:px-6 lg:px-12 py-8">
      {/* Fallback warning message if critical data is missing */}
      {!hasCriticalData && (
        <div className="mb-6 border border-yellow-200 bg-yellow-50 text-yellow-800 rounded-xl p-4">
          <h2 className="text-lg font-semibold mb-2">Your Dashboard is Not Fully Ready</h2>
          <p className="text-sm">Some financial data could not be loaded yet. Please ensure your accounts are linked and try refreshing.</p>
          <ul className="text-sm mt-2 space-y-1">
            {(!netWorth || !netWorth.units || netWorth.units === 0) && (
              <li>✖ Net Worth data unavailable</li>
            )}
            {(!creditScore || creditScore <= 0) && (
              <li>✖ Credit Score data unavailable</li>
            )}
            {(!Array.isArray(assetAllocation) || assetAllocation.length === 0) && (
              <li>✖ Asset Allocation missing</li>
            )}
          </ul>
          <div className="mt-2">
            <Button variant="secondary" onClick={() => window.location.reload()}>Refresh Dashboard</Button>
          </div>
        </div>
      )}
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="flex flex-wrap justify-between items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">
              Financial Overview
            </h1>
            <p className="text-slate-500">Welcome back, {mobileNumber || "User"}. Here’s what’s new.</p>
            <p className="text-xs text-slate-400 mt-1">Last updated: {new Date().toLocaleTimeString()}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className={`flex h-2 w-2 rounded-full ${epf ? 'bg-green-500' : 'bg-slate-300'}`}></span> EPF
              <span className={`flex h-2 w-2 rounded-full ${(Array.isArray(stocks) && stocks.length > 0) ? 'bg-green-500' : 'bg-slate-300'}`}></span> Stocks
              <span className={`flex h-2 w-2 rounded-full ${creditReport?.creditReportData ? 'bg-green-500' : 'bg-slate-300'}`}></span> Credit
            </div>
            <Button variant="outline" size="icon" className="text-slate-500 border-slate-300 hover:bg-slate-100 hover:text-slate-800 rounded-full">
              <Bell className="w-5 h-5" />
            </Button>
          </div>
        </header>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-6 justify-between">
          {[
            {
              title: 'Net Worth',
              Icon: IndianRupee,
              value: stableNetWorth?.units && stableNetWorth.units > 0 ? `₹${stableNetWorth.units.toLocaleString('en-IN')}` : "Not Available",
              change: `+₹${(dailyChange / 1000).toFixed(0)}K today`,
              changeColor: 'text-green-600',
              iconBg: 'bg-teal-100 text-teal-600',
              isCritical: stableNetWorth && stableNetWorth.units < 1000000 // <10L
            },
            {
              title: 'Credit Score',
              Icon: Shield,
              value: (stableCreditScore ?? creditScore) && (stableCreditScore ?? creditScore) > 0 ? (stableCreditScore ?? creditScore) : "Unavailable",
              change: creditLabel,
              changeColor: getCreditScoreColor(stableCreditScore ?? creditScore),
              iconBg: 'bg-sky-100 text-sky-600',
              isCritical: (stableCreditScore ?? creditScore) < 600
            },
            {
              title: 'Risk Level',
              Icon: Activity,
              value: `${computedRiskLevel}%`,
              change: computedRiskLevel > 50 ? 'High' : 'Low',
              changeColor: computedRiskLevel > 50 ? 'text-orange-600' : 'text-slate-500',
              iconBg: 'bg-orange-100 text-orange-600',
              isCritical: computedRiskLevel > 60
            },
          ].map(item =>
            item.title === 'Credit Score' ? (
              <div
                key={item.title}
                onClick={() => item.title === 'Credit Score' && (stableCreditScore ?? creditScore) > 0 ? handleCardClick("Explain my credit score trends") : null}
                style={{ cursor: 'pointer' }}
              >
                <Card
                  className={`bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel ${
                    item.isCritical ? 'border-red-500 animate-pulse' : ''
                  }`}
                >
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium text-slate-500 flex items-center">
                      {item.isCritical && (
                        <span className="text-red-500 text-xs font-semibold animate-bounce mr-2">⚠️</span>
                      )}
                      {item.title}
                      <span className="ml-1 text-xs text-slate-400 cursor-help" title="This is calculated from your linked accounts.">ℹ️</span>
                    </CardTitle>
                    <div className={`p-2 rounded-full ${item.iconBg}`}>
                      <item.Icon className="h-4 w-4" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-slate-900">{item.value}</div>
                    <p className={`text-xs ${item.changeColor}`}>{item.change}</p>
                  </CardContent>
                </Card>
              </div>
            ) : item.title === 'Net Worth' ? (
              <Card
                key={item.title}
                className={`bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel ${
                  item.isCritical ? 'border-red-500 animate-pulse' : ''
                }`}
              >
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-slate-500 flex items-center">
                    {item.isCritical && (
                      <span className="text-red-500 text-xs font-semibold animate-bounce mr-2">⚠️</span>
                    )}
                    {item.title}
                    <span className="ml-1 text-xs text-slate-400 cursor-help" title="This is calculated from your linked accounts.">ℹ️</span>
                  </CardTitle>
                  <div className={`p-2 rounded-full ${item.iconBg}`}>
                    <item.Icon className="h-4 w-4" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-slate-900">{item.value}</div>
                  <p className={`text-xs ${item.changeColor}`}>{item.change}</p>
                </CardContent>
              </Card>
            ) : (
              <Card
                key={item.title}
                className={`bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel ${
                  item.isCritical ? 'border-red-500 animate-pulse' : ''
                }`}
              >
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-slate-500 flex items-center">
                    {item.isCritical && (
                      <span className="text-red-500 text-xs font-semibold animate-bounce mr-2">⚠️</span>
                    )}
                    {item.title}
                  </CardTitle>
                  <div className={`p-2 rounded-full ${item.iconBg}`}>
                    <item.Icon className="h-4 w-4" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-slate-900">{item.value}</div>
                  <p className={`text-xs ${item.changeColor}`}>{item.change}</p>
                </CardContent>
              </Card>
            )
          )}
        </div>
        {/* Overview Section: Bank/Credit Summary Cards */}
     
        {/* Account Summary - Compact Card */}
        <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl flex flex-col justify-between backdrop-blur-sm backdrop-filter shadow-pastel">
          <CardHeader className="flex flex-row justify-between items-start">
            <div>
              <CardTitle>Account Summary</CardTitle>
              <CardDescription className="text-slate-500">Overview of all linked accounts</CardDescription>
            </div>
            <Button variant="outline" size="sm" className="text-slate-600 border-slate-300" onClick={() => setShowAccountModal(true)}>
              View All
            </Button>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-1">
              <div className="text-2xl font-bold text-slate-900">
                {Object.keys(accounts || {}).length} Accounts
              </div>
              <div className="text-sm text-slate-500">
                Total Value: ₹{Object.values(accounts || {}).reduce((sum, acc) => {
                  let balance = 0;
                  if (acc.depositSummary?.currentBalance?.units)
                    balance = parseInt(acc.depositSummary.currentBalance.units);
                  else if (acc.creditCardSummary?.currentBalance?.units)
                    balance = parseInt(acc.creditCardSummary.currentBalance.units);
                  else if (acc?.epfSummary?.currentValue?.units)
                    balance = parseInt(acc.epfSummary.currentValue.units);
                  else if (acc?.mutualFundSummary?.currentValue?.units)
                    balance = parseInt(acc.mutualFundSummary.currentValue.units);
                  else if (acc?.etfSummary?.currentValue?.units)
                    balance = parseInt(acc.etfSummary.currentValue.units);
                  else if (acc?.equitySummary?.currentValue?.units)
                    balance = parseInt(acc.equitySummary.currentValue.units);
                  else if (acc?.sgbSummary?.currentValue?.units)
                    balance = parseInt(acc.sgbSummary.currentValue.units);
                  return sum + balance;
                }, 0).toLocaleString('en-IN')}
              </div>
            </div>
          </CardContent>
        </Card>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-6 justify-between">
          <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader>
              <CardTitle>Total Credit Limit</CardTitle>
              <CardDescription className="text-slate-500">Summed across all linked credit cards</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-900">
                ₹{(() => {
                  const creditAccs = Object.values(accounts || {}).filter(acc => acc?.accountDetails?.accInstrumentType === "ACC_INSTRUMENT_TYPE_CREDIT_CARD");
                  const total = creditAccs.reduce((sum, acc) => sum + parseInt(acc?.creditCardSummary?.creditLimit?.units || 0), 0);
                  return total.toLocaleString('en-IN');
                })()}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader>
              <CardTitle>Current Credit Usage</CardTitle>
              <CardDescription className="text-slate-500">Outstanding balance across credit cards</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-slate-900">
                ₹{(() => {
                  const creditAccs = Object.values(accounts || {}).filter(acc => acc?.accountDetails?.accInstrumentType === "ACC_INSTRUMENT_TYPE_CREDIT_CARD");
                  const total = creditAccs.reduce((sum, acc) => sum + parseInt(acc?.creditCardSummary?.currentBalance?.units || 0), 0);
                  return total.toLocaleString('en-IN');
                })()}
              </div>
            </CardContent>
          </Card>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 justify-between">
          <Card className="lg:col-span-2 bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader>
              <CardTitle>Asset Allocation</CardTitle>
              <CardDescription className="text-slate-500">Your portfolio distribution</CardDescription>
            </CardHeader>
            <CardContent>
              {assetAllocation.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={assetAllocation}
                        cx="50%"
                        cy="50%"
                        innerRadius={80}
                        outerRadius={110}
                        paddingAngle={3}
                        dataKey="value"
                      >
                        {(Array.isArray(assetAllocation) ? assetAllocation : []).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} stroke={entry.color} className="focus:outline-none focus:ring-2 focus:ring-offset-2" style={{ filter: `drop-shadow(0px 2px 4px ${entry.color}60)` }} />
                        ))}
                      </Pie>
                      <Tooltip
                        cursor={{ fill: 'rgba(203, 213, 225, 0.3)' }}
                        contentStyle={{ backgroundColor: 'white', borderRadius: '0.75rem', borderColor: '#e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)' }}
                        formatter={(value, name) => [`₹${(value / 100000).toLocaleString('en-IN', { maximumFractionDigits: 1 })}L`, name.charAt(0).toUpperCase() + name.slice(1).toLowerCase()]}
                      />
                      <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '20px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </>
              ) : (
                <div className="text-center text-slate-500 py-16">Asset data is currently unavailable.</div>
              )}
            </CardContent>
          </Card>
        </div>
        {/* Transaction Timeline Card with LineChart */}
        <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
          <CardHeader>
            <CardTitle>Transaction Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            {timelineData?.length > 0 ? (
              <div className="min-h-[320px] h-[35vh]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={timelineData.map(d => ({
                      date: d.date,
                      count: d.txns.length,
                      value: d.txns.reduce((sum, txn) => sum + (txn.amount ?? txn.transactionAmount ?? 0), 0)
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="left" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis yAxisId="right" orientation="right" stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: 'white', borderRadius: '0.75rem', borderColor: '#e2e8f0' }}
                      formatter={(value, name) => name === 'count'
                        ? [`${value} txns`, 'Count']
                        : [`₹${(+value).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`, 'Value']
                      }
                    />
                    <Line
                      yAxisId="left"
                      type="monotone"
                      dataKey="count"
                      name="Count"
                      stroke="#0D9488"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ onClick: handleTimelineClick }}
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="value"
                      name="Value"
                      stroke="#6366F1"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ onClick: handleTimelineClick }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="text-center py-10 text-slate-500">No timeline data available</div>
            )}
          </CardContent>
        </Card>
        <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription className="text-slate-500">Perform common tasks with one click.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[
              { icon: MessageCircle, text: 'Ask AI Assistant', primary: true },
              { icon: Target, text: 'Set Financial Goal' },
              { icon: BarChart3, text: 'Run Simulation' },
              { icon: Upload, text: 'Upload Documents' },
            ].map((action, i) => (
              <Button key={i} variant={action.primary ? "default" : "outline"} className={`h-24 flex-col gap-2 transition-all duration-300 text-sm ${action.primary ? 'bg-teal-600 hover:bg-teal-700' : 'border-slate-300 text-slate-600 hover:border-teal-500 hover:bg-teal-50 hover:text-teal-600'}`}>
                <action.icon className="w-6 h-6" />
                {action.text}
              </Button>
            ))}
          </CardContent>
        </Card>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 justify-between">
          {/* EPF Summary - Compact Card */}
          <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl flex flex-col justify-between backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader className="flex flex-row justify-between items-start">
              <div>
                <CardTitle>EPF Summary</CardTitle>
                <CardDescription className="text-slate-500">Provident fund overview</CardDescription>
              </div>
              <Button variant="outline" size="sm" className="text-slate-600 border-slate-300" onClick={() => setShowEpfModal(true)}>
                View All
              </Button>
            </CardHeader>
            <CardContent className="min-h-[80px]">
              {(epf?.summary?.establishment_count || 0) > 0 ? (
                <div>
                  <div className="text-2xl font-bold text-slate-900">
                    {epf.summary.establishment_count} Companies Linked
                  </div>
                  <div className="text-sm text-slate-500">
                    Total EPF: ₹{parseInt(epf.summary.total_pf_balance || 0).toLocaleString('en-IN')}
                  </div>
                </div>
              ) : (
                <div className="text-center py-4 text-slate-500">No EPF data linked</div>
              )}
            </CardContent>
          </Card>
          {/* Recent Bank Transactions (unchanged) */}
          <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader className="flex flex-row justify-between items-start">
              <div>
                <CardTitle>Recent Bank Transactions</CardTitle>
                <CardDescription className="text-slate-500">Last 8 activities</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {(Array.isArray(safeBankTransactions) && safeBankTransactions.length > 0) ? (
                <div className="space-y-1">
                  {safeBankTransactions.slice(-8).reverse().map((txn, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 rounded-lg hover:bg-slate-100">
                      <div className="text-sm text-slate-600 max-w-[65%] truncate">{txn.description || txn.narration || "Transaction"}</div>
                      <div className={`text-sm text-right font-medium font-mono ${txn.amount >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {txn.amount >= 0 ? '+' : '-'}₹{(Math.abs(txn.amount) / 1000).toFixed(1)}K
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-10 text-slate-500">No recent bank transactions</div>
              )}
            </CardContent>
          </Card>
        </div>
        {/* Stock and Mutual Fund Expanded Views */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 justify-between">
          <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader className="flex flex-row justify-between items-center">
              <div>
                <CardTitle>Stock Holdings</CardTitle>
                <CardDescription className="text-slate-500">Recent stock transactions</CardDescription>
              </div>
              <Button variant="outline" size="sm" className="text-slate-600 border-slate-300" onClick={() => setShowStockModal(true)}>
                View All
              </Button>
            </CardHeader>
            <CardContent>
              {(Array.isArray(safeStocks) && safeStocks.length > 0) ? (
                <div className="space-y-4">
                  {safeStocks.map((stock, i) => (
                    <div key={i} className="p-2 rounded-lg border border-slate-100 bg-slate-50">
                      <div className="flex justify-between items-center mb-1">
                        <span className="font-semibold text-teal-700">{stock.isin}</span>
                        <span className="text-xs text-slate-400">{Array.isArray(stock.txns) ? stock.txns.length : 0} txns</span>
                      </div>
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-slate-500">
                            <th className="text-left p-1">Type</th>
                            <th className="text-left p-1">Date</th>
                            <th className="text-left p-1">Qty</th>
                            <th className="text-left p-1">NAV</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(Array.isArray(stock.txns) ? stock.txns.slice(-3).reverse() : []).map((txn, idx) => (
                            <tr key={idx}>
                              <td className={`p-1 font-mono font-medium ${txn[0] === 1 ? 'text-green-600' : 'text-red-600'}`}>{txn[0] === 1 ? 'Buy' : 'Sell'}</td>
                              <td className="p-1 font-mono tabular-nums text-slate-600">{new Date(txn[1]).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                              <td className="p-1 font-mono tabular-nums text-slate-600">{txn[2]}</td>
                              <td className="p-1 font-mono tabular-nums text-slate-600">₹{txn[3]}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-10 text-slate-500">No stock data</div>
              )}
            </CardContent>
          </Card>
          <Card className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
            <CardHeader>
              <CardTitle>Mutual Fund Transactions</CardTitle>
              <CardDescription className="text-slate-500">Recent mutual fund activity</CardDescription>
            </CardHeader>
            <CardContent>
              {(Array.isArray(safeMfTransactions) && safeMfTransactions.length > 0) ? (
                <div className="space-y-2">
                  {safeMfTransactions.slice(-5).reverse().map((txn, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 rounded-lg hover:bg-slate-100">
                      <div className="text-xs text-slate-700 font-semibold">{txn.scheme_name}</div>
                      <div className="flex items-center gap-4">
                        <span className={`font-mono text-xs ${txn.txn_type === 'PURCHASE' ? 'text-green-600' : 'text-red-600'}`}>{txn.txn_type}</span>
                        <span className="font-mono text-xs text-slate-600">
                          {txn.txn_date && !isNaN(new Date(txn.txn_date)) ? new Date(txn.txn_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Unknown Date'}
                        </span>
                        <span className="font-mono text-xs text-slate-600">₹{!isNaN(+txn.amount) ? (+txn.amount).toLocaleString('en-IN') : '—'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-10 text-slate-500">No mutual fund transactions</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
      {/* Account Summary Modal */}
      <Dialog open={showAccountModal} onOpenChange={setShowAccountModal}>
        <DialogContent className="bg-white max-w-3xl rounded-xl">
          <DialogHeader>
            <DialogTitle className="text-xl text-slate-900">All Accounts</DialogTitle>
            <DialogDescription className="text-slate-500">
              Detailed view of all your linked accounts.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[60vh] overflow-y-auto mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(accounts || {}).map(([key, acc], idx) => {
              const type = acc?.accountDetails?.accInstrumentType?.replace("ACC_INSTRUMENT_TYPE_", "")?.replace(/_/g, " ");
              const number = acc?.maskedAccountNumber || "XXXX";
              const fip = acc?.fipId || "Unknown";
              let balance = 0;
              if (acc.depositSummary?.currentBalance?.units)
                balance = parseInt(acc.depositSummary.currentBalance.units);
              else if (acc.creditCardSummary?.currentBalance?.units)
                balance = parseInt(acc.creditCardSummary.currentBalance.units);
              else if (acc?.epfSummary?.currentValue?.units)
                balance = parseInt(acc.epfSummary.currentValue.units);
              else if (acc?.mutualFundSummary?.currentValue?.units)
                balance = parseInt(acc.mutualFundSummary.currentValue.units);
              else if (acc?.etfSummary?.currentValue?.units)
                balance = parseInt(acc.etfSummary.currentValue.units);
              else if (acc?.equitySummary?.currentValue?.units)
                balance = parseInt(acc.equitySummary.currentValue.units);
              else if (acc?.sgbSummary?.currentValue?.units)
                balance = parseInt(acc.sgbSummary.currentValue.units);
              return (
                <Card key={idx} className="bg-white p-5 sm:p-6 lg:p-8 shadow-md hover:shadow-lg transition-transform transform hover:scale-[1.01] border border-slate-200/80 rounded-xl backdrop-blur-sm backdrop-filter shadow-pastel">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-slate-600">{type || "Account"}</CardTitle>
                    <CardDescription className="text-xs text-slate-400">{fip} - {number}</CardDescription>
                  </CardHeader>
                  <CardContent className="text-lg font-mono text-slate-800">
                    ₹{balance.toLocaleString('en-IN')}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </DialogContent>
      </Dialog>

      {/* EPF Summary Modal */}
      <Dialog open={showEpfModal} onOpenChange={setShowEpfModal}>
        <DialogContent className="bg-white max-w-2xl rounded-xl">
          <DialogHeader>
            <DialogTitle className="text-xl text-slate-900">EPF Details</DialogTitle>
            <DialogDescription className="text-slate-500">
              Company-wise provident fund details.
            </DialogDescription>
          </DialogHeader>
          <div className="overflow-x-auto mt-4">
            {(epf?.uanAccounts?.[0]?.rawDetails?.est_details?.length || 0) > 0 ? (
              <table className="w-full text-sm">
                <thead className="bg-slate-100">
                  <tr>
                    <th className="text-left font-semibold text-slate-600 px-4 py-2 rounded-tl-lg">Company</th>
                    <th className="text-right font-semibold text-slate-600 px-4 py-2">Employee</th>
                    <th className="text-right font-semibold text-slate-600 px-4 py-2">Employer</th>
                    <th className="text-right font-semibold text-slate-600 px-4 py-2 rounded-tr-lg">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {epf.uanAccounts[0].rawDetails.est_details.map((item, idx) => {
                    const emp = parseInt(item?.pf_balance?.employee_share?.balance || "0");
                    const emr = parseInt(item?.pf_balance?.employer_share?.balance || "0");
                    return (
                      <tr key={idx} className="border-b border-slate-200 last:border-0 odd:bg-white even:bg-slate-50">
                        <td className="text-left px-4 py-3 font-medium">{item.est_name}</td>
                        <td className="text-right font-mono px-4 py-3">₹{(emp / 100000).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}L</td>
                        <td className="text-right font-mono px-4 py-3">₹{(emr / 100000).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}L</td>
                        <td className="text-right font-mono px-4 py-3 font-semibold text-slate-900">₹{((emp + emr) / 100000).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}L</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <div className="text-center py-10 text-slate-500">No EPF data linked</div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Stock Modal Dialog with Chart */}
      <Dialog open={showStockModal} onOpenChange={setShowStockModal}>
        <DialogContent className="bg-white max-w-3xl rounded-xl">
          <DialogHeader>
            <DialogTitle className="text-xl text-slate-900">All Stock Transactions</DialogTitle>
            <DialogDescription className="text-slate-500">
              A complete history of your stock trading activity.
            </DialogDescription>
          </DialogHeader>
          <div className="mb-6">
            {Array.isArray(safeStocks) && safeStocks.length > 0 && Array.isArray(safeStocks[0].txns) && safeStocks[0].txns.length > 1 && (
              <div onClick={() => handleCardClick("Explain stock performance")} className="cursor-pointer">
                <ResponsiveContainer width="100%" height={180}>
                  <LineChart
                    data={safeStocks[0].txns
                      .slice()
                      .sort((a, b) => new Date(a[1]) - new Date(b[1]))
                      .map(txn => ({
                        date: new Date(txn[1]).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }),
                        nav: txn[3]
                      }))
                    }
                  >
                    <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                    <Tooltip contentStyle={{ backgroundColor: 'white', borderRadius: '0.75rem', borderColor: '#e2e8f0' }} />
                    <Line type="monotone" dataKey="nav" stroke="#0D9488" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
          <div className="max-h-[50vh] overflow-y-auto space-y-4 pr-3 mt-4">
            {Array.isArray(safeStocks) && safeStocks.map((stock, i) => (
              <div key={i} className="p-3 rounded-lg border border-slate-200 bg-slate-50">
                <p className="font-semibold text-teal-700 mb-2">{stock.isin}</p>
                <table className="w-full text-xs">
                  <thead className="border-b border-slate-300">
                    <tr className="text-slate-500">
                      <th className="text-left p-2 font-semibold">Type</th>
                      <th className="text-left p-2 font-semibold">Date</th>
                      <th className="text-left p-2 font-semibold">Quantity</th>
                      <th className="text-left p-2 font-semibold">NAV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(Array.isArray(stock.txns) ? stock.txns.slice().sort((a, b) => new Date(b[1]) - new Date(a[1])) : []).map((txn, idx) => (
                      <tr key={idx} className="hover:bg-slate-200/50 border-b border-slate-200 last:border-0">
                        <td className={`p-2 font-mono font-medium ${txn[0] === 1 ? 'text-green-600' : 'text-red-600'}`}>{txn[0] === 1 ? 'Buy' : 'Sell'}</td>
                        <td className="p-2 font-mono tabular-nums text-slate-600">{new Date(txn[1]).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}</td>
                        <td className="p-2 font-mono tabular-nums text-slate-600">{txn[2]}</td>
                        <td className="p-2 font-mono tabular-nums text-slate-600">₹{txn[3]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};


export default Dashboard;