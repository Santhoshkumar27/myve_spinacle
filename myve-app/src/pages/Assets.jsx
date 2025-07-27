import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ResponsiveSunburst } from '@nivo/sunburst';
import { useMcp } from '../context/McpContext';

// --- Updated color palette to match the light theme ---
const formatAssetAllocation = (assets) => {
  const colors = ["#14B8A6", "#38BDF8", "#F97316", "#8B5CF6", "#6366F1", "#EC4899"];
  if (!Array.isArray(assets)) return [];
  
  return assets.map((asset, index) => ({
    name: asset.netWorthAttribute.replace("ASSET_TYPE_", "").replace(/_/g, " "),
    value: Number(asset?.value?.units || 0),
    color: colors[index % colors.length],
  }));
};

const Assets = () => {
  const { finalSnapshot } = useMcp();
  const assets = Array.isArray(finalSnapshot?.assets) ? finalSnapshot.assets : [];
  const isLoading = finalSnapshot == null;

  const assetAllocation = formatAssetAllocation(assets);
  const totalAssetsValue = assetAllocation.reduce((acc, asset) => acc + asset.value, 0);

  const sortedAssets = [...assetAllocation].sort((a, b) => b.value - a.value);
  const topHoldings = sortedAssets.slice(0, 3);
  const topAsset = topHoldings[0];
  const diversificationScore = Math.min(100, (assetAllocation.length / 10) * 100);
  const topAssetWeight = topAsset ? (topAsset.value / totalAssetsValue) * 100 : 0;

  // --- Start of Enhanced UI Rendering ---
  return (
    <div className="bg-gradient-to-br from-green-50 to-white text-slate-800 min-h-screen p-4 sm:p-5 lg:p-6">
      <style>{`
        .shadow-pastel {
          box-shadow: 0 4px 6px -1px rgba(56, 189, 248, 0.1), 0 2px 4px -1px rgba(56, 189, 248, 0.06);
        }
      `}</style>
      <div className="max-w-7xl mx-auto space-y-6">
        {/* --- Enhanced Header --- */}
        <header>
          <h1 className="text-3xl font-bold text-slate-900">Asset Intelligence</h1>
          <p className="text-slate-500 mt-1">
            A detailed breakdown and analysis of your portfolio holdings.
          </p>
        </header>

        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <div className="flex flex-col items-center space-y-4">
              <svg className="w-12 h-12 animate-spin text-teal-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <p className="text-lg text-slate-600">Analyzing your assets...</p>
            </div>
          </div>
        ) : assetAllocation.length > 0 ? (
          <div className="space-y-6">
            {/* --- Pie/Sunburst Chart Card at the Top --- */}
            <Card className="p-4 shadow-md border border-gray-200 rounded-lg">
              <CardHeader>
                <CardTitle>Portfolio Distribution</CardTitle>
                <CardDescription>
                  Total Asset Value: <span className="font-semibold text-teal-600">₹{(totalAssetsValue / 100000).toFixed(1)}L</span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[260px] mb-4">
                  <ResponsiveSunburst
                    data={{
                      name: 'Total Assets',
                      children: assetAllocation.map(asset => ({
                        name: asset.name,
                        loc: asset.value,
                        color: asset.color
                      }))
                    }}
                    margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
                    identity={(d) => `${d.name} (${(d.loc / 100000).toFixed(1)}L)`}
                    value="loc"
                    colors={{ datum: 'data.color' }}
                    cornerRadius={2}
                    borderColor={{ theme: 'background' }}
                    childColor={{ from: 'color' }}
                    animate={true}
                    motionConfig="gentle"
                    tooltip={({ id, value, color }) => (
                      <div style={{
                        padding: 8,
                        background: 'white',
                        border: `1px solid #e2e8f0`,
                        borderRadius: 8,
                        color: '#0f172a'
                      }}>
                        <strong style={{ color }}>{id}</strong>
                      </div>
                    )}
                  />
                </div>
                {/* Top Holdings, Diversification Score, Warnings */}
                <div className="space-y-3">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-600 mb-1 uppercase tracking-wide">Top Holdings</h3>
                    <ul className="text-sm text-slate-800 space-y-1">
                      {topHoldings.map((h, idx) => (
                        <li key={idx} className="flex justify-between">
                          <span className="flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: h.color }}></span>
                            {h.name}
                          </span>
                          <span>₹{(h.value / 100000).toFixed(1)}L</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-600 mb-1">Diversification Score</h3>
                    <p className="text-sm text-slate-700">{diversificationScore.toFixed(0)}% – {diversificationScore < 40 ? "Low" : diversificationScore < 70 ? "Moderate" : "High"}</p>
                  </div>
                  {topAssetWeight > 50 && (
                    <div className="text-sm text-orange-600 bg-orange-50 p-2 rounded-lg border border-orange-200">
                      ⚠️ Your portfolio is heavily concentrated in <strong>{topAsset.name}</strong> ({topAssetWeight.toFixed(1)}% of total). Consider rebalancing.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
            {/* --- Individual Asset Cards, Stacked --- */}
            {assetAllocation.map((asset) => (
              <Card key={asset.name} className="p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-lg">{asset.name}
                    <span className="text-xs text-slate-500 block mt-1">Asset Type</span>
                  </CardTitle>
                  <CardDescription>Current Holdings</CardDescription>
                </CardHeader>
                <CardContent className="flex justify-between items-center">
                  <div className="text-2xl font-bold text-slate-800">
                    ₹{(asset.value / 100000).toFixed(1)}L
                  </div>
                  {/* The risk badge can be made dynamic if risk data is available */}
                  <Badge className="bg-orange-100 text-orange-700 border border-orange-200">Moderate Risk</Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="bg-white p-10 text-center shadow-pastel hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border border-slate-200/80 rounded-2xl">
            <div className="max-w-md mx-auto">
              <svg className="w-16 h-16 mx-auto text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
              </svg>
              <CardTitle className="mt-4 text-xl font-semibold text-slate-800">Start Building Your Portfolio</CardTitle>
              <CardDescription className="mt-1 text-slate-500">
                We couldn't find any linked assets yet. To unlock personalized insights and analytics, please add your investments like Mutual Funds, Stocks, or EPF accounts.
              </CardDescription>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Assets;