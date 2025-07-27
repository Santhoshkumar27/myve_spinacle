import React, { useState, useEffect } from 'react';
import Dashboard from './pages/Dashboard';
import Assets from './pages/Assets';
import CreditHealth from './pages/CreditHealth';
import DataSim from './pages/DataSim';
import GoalPlanner from './pages/DataSim';
import ChatAssistant from './pages/ChatAssistant';
import UploadCenter from './pages/UploadCenter';
import Reports from './pages/Reports';
import SettingsPage from './pages/Settings';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend,
  BarChart,
  Bar
} from 'recharts';
import { 
  DollarSign, 
  TrendingUp, 
  TrendingDown, 
  Shield, 
  Upload, 
  MessageCircle, 
  Download,
  CreditCard,
  PiggyBank,
  Target,
  Settings,
  Bell,
  User,
  LogOut,
  Home,
  BarChart3,
  FileText,
  Bot,
  Wallet,
  Activity,
  X
} from 'lucide-react';
import { McpProvider } from "./context/McpContext";
import { useMcp } from "./context/McpContext";
import McpLoginModal from "./components/McpLoginModal";



// Navigation Component
const Navigation = ({ activeTab, setActiveTab }) => {
  const { isConnected, openModal, disconnect, isModalOpen, closeModal, mobileNumber } = useMcp();

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home },
    { id: 'assets', label: 'Assets', icon: BarChart3 },
    { id: 'credit', label: 'Credit Health', icon: CreditCard },
    { id: 'chat', label: 'Ask myve.', icon: Bot },
    { id: 'upload', label: 'Upload Center', icon: Upload },
    { id: 'reports', label: 'Reports', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings }
  ];

  return (
    <div className="relative w-full h-full">
      <div className="w-64 bg-card border-r border-border h-full md:h-screen p-4 relative">
        <div className="flex items-center gap-2 mb-8">
          <img src="src/assets/myve_logo.png" alt="Myve Logo" className="h-16" />
        </div>
        
        <nav className="space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                  activeTab === item.id 
                    ? 'bg-primary text-primary-foreground' 
                    : 'hover:bg-accent hover:text-accent-foreground'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="absolute bottom-4 left-4 right-4">
          <div className="flex items-center gap-3 p-3 bg-accent rounded-lg">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-primary-foreground" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium">{mobileNumber || "User"}</p>
              <p className="text-xs text-muted-foreground">
                {isConnected ? "MCP Connected" : "Not Connected"}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={async () => {
                try {
                  openModal(); // trigger only the custom modal
                } catch (err) {
                  console.error("MCP Login error:", err);
                  openModal();
                }
              }}
            >
              {isConnected ? <Settings className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {isModalOpen && (
          <McpLoginModal
            isOpen={isModalOpen}
            onClose={closeModal}
            onSuccess={(number) => {
              // This callback is now handled at App level
            }}
          />
        )}
      </div>
      <button
        onClick={() => setActiveTab(null)}
        className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 md:hidden"
      >
        <X className="w-5 h-5" />
      </button>
    </div>
  );
};


function App() {
  const [activeTab, setActiveTab] = useState(() => localStorage.getItem("activeTab") || "dashboard");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [visionMode, setVisionMode] = useState(false);
  const { isConnected, setNetWorth, setAssets, setCreditSummary, isModalOpen, openModal, closeModal, setMobileNumber, netWorth, assets, creditSummary } = useMcp();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (isConnected && !netWorth && assets.length === 0 && !creditSummary) {
      const fetchOnce = async () => {
        const netRes = await fetch("/api/mcp/networth", { credentials: "include" });
        const net = netRes.ok ? await netRes.json() : {};
        const cred = await fetch("/api/mcp/credit", { credentials: "include" }).then(r => r.json());
        const asset = await fetch("/api/mcp/assets", { credentials: "include" }).then(r => r.json());

        setNetWorth(net.netWorth?.units || 0);
        setAssets(asset);
        setCreditSummary(cred.summary || {});
      };
      fetchOnce();
    }
  }, [isConnected, netWorth, assets, creditSummary]);

  useEffect(() => {
    localStorage.setItem("activeTab", activeTab);
  }, [activeTab]);

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'assets':
        return <Assets />;
      case 'credit':
        return <CreditHealth />;
      case 'goals':
        return <GoalPlanner />;
      case 'chat':
        return <ChatAssistant />;
      case 'upload':
        return <UploadCenter />;
      case 'reports':
        return <Reports />;
      case 'settings':
        return <SettingsPage />;
      default:
        return <Dashboard />;
    }
  };

  const handleVisionToggle = async () => {
    const mobileNumber = localStorage.getItem("user_mobile");
    try {
      await fetch("/api/vision/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: visionMode ? "stop" : "start",
          user: mobileNumber
        })
      });
      setVisionMode(!visionMode);
    } catch (err) {
      console.error("Vision control failed:", err);
      alert("Failed to toggle Vision.");
    }
  };

  return (
    <div className="flex flex-col md:flex-row h-screen overflow-hidden bg-gradient-to-br from-green-50 to-white text-slate-800">
      <div className="block md:hidden p-4">
        <button
          onClick={() => setMobileMenuOpen(prev => !prev)}
          className="p-2 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100"
        >
          ☰
        </button>
      </div>
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-y-0 left-0 w-64 z-40 bg-white shadow-lg">
          <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />
        </div>
      )}
      <div className="hidden md:block">
        <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
      <main className="flex-1 min-h-0 max-h-screen overflow-y-auto p-4 sm:p-6 md:p-8 lg:p-10 transition-all duration-300">
        {renderContent()}
      </main>

      {isModalOpen && (
        <McpLoginModal
          isOpen={isModalOpen}
          onClose={closeModal}
          onSuccess={(number) => {
            setMobileNumber(number);
            setPhoneNumber(number);
            localStorage.setItem("user_mobile", number); // ✅ Add this
            console.log('MCP Connected');
          }}
        />
      )}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3">
        <button
          onClick={handleVisionToggle}
          className={`flex items-center gap-4 px-10 py-6 text-3xl rounded-full shadow-lg transition-all duration-300 transform hover:scale-105 ${
            visionMode ? "bg-gray-800 text-white" : "bg-black text-white hover:bg-black/90"
          }`}
        >
          <img src="src/assets/logow.svg" alt="myve logo" className="w-10 h-10" />
          <span>{visionMode ? "Visualising..." : "Vision."}</span>
        </button>

      </div>
    </div>
  );
}

export default App;
