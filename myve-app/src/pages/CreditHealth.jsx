import React from 'react';
import { useMcp } from '../context/McpContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

const Credit = () => {
  // 1. Extend useMcp to extract creditReport
  const { creditReport } = useMcp();
  // 7. Update loading condition to use both
  const loading = !creditReport || !creditReport?.creditReportData;

  if (!creditReport || Object.keys(creditReport).length === 0) {
    return (
      <Card className="shadow-md border border-gray-200 rounded-lg">
        <CardHeader>
          <CardTitle className="text-primary font-semibold">No Credit Data Available</CardTitle>
          <CardDescription className="text-muted-foreground">Credit report is not available for this user.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const score = creditReport?.creditReportData?.score?.bureauScore ?? 0;
  const creditSeverity = score >= 750 ? 'text-green-600' : score >= 650 ? 'text-yellow-600' : 'text-red-600';

  const defaults = creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.account?.creditAccountDefault ?? 0;
  const defaultClass = defaults > 0 ? 'text-red-600 font-semibold animate-pulse' : '';

  const capsCount = creditReport?.creditReportData?.caps?.capsSummary?.capsLast180Days ?? 0;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Credit Health</h2>
      {loading ? (
        <div>Loading credit report...</div>
      ) : (
        <>
          {/* Fallback card if no creditReportData */}
          {!creditReport?.creditReportData && (
            <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
              <CardHeader>
                <CardTitle className="text-primary font-semibold text-xl">No Credit Report</CardTitle>
                <CardDescription className="text-muted-foreground">User may not have any credit history</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  We couldn't find any credit report data for this user.
                </div>
              </CardContent>
            </Card>
          )}

          {/* Credit Score & Accounts Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {!creditReport?.creditReportData?.score?.bureauScore ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No Credit Score Available</CardTitle>
                  <CardDescription className="text-muted-foreground">We couldn't retrieve a credit score for this user.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">Credit Score</CardTitle>
                  <CardDescription className="text-muted-foreground">Your latest score</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className={`text-2xl font-bold ${creditSeverity}`}>
                    {score}
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    {score < 600 ? '⚠️ Low credit score. Improve payment history and credit utilization.' :
                     score < 750 ? '🟡 Average score. Maintain timely payments to improve.' :
                     '✅ Excellent score! Keep it up.'}
                  </div>
                </CardContent>
              </Card>
            )}

            {!creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.account ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No Accounts Overview Available</CardTitle>
                  <CardDescription className="text-muted-foreground">Account summary data is missing.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">Accounts Overview</CardTitle>
                  <CardDescription className="text-muted-foreground">Open, Closed, Default</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 text-sm">
                    <li>
                      Total: <span className="font-semibold">{(creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.account?.creditAccountTotal ?? (creditReport?.creditReportData ? 0 : "N/A")).toLocaleString("en-IN")}</span>
                    </li>
                    <li>
                      Active: <span className="font-semibold">{(creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.account?.creditAccountActive ?? (creditReport?.creditReportData ? 0 : "N/A")).toLocaleString("en-IN")}</span>
                    </li>
                    <li>
                      Closed: <span className="font-semibold">{(creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.account?.creditAccountClosed ?? (creditReport?.creditReportData ? 0 : "N/A")).toLocaleString("en-IN")}</span>
                    </li>
                    <li>
                      Defaults: <span className={`${defaultClass}`}>{defaults}</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {/* Outstanding Balances */}
            {!creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.totalOutstandingBalance ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No Outstanding Balances Available</CardTitle>
                  <CardDescription className="text-muted-foreground">Outstanding balance data is missing.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">Outstanding Balances</CardTitle>
                  <CardDescription className="text-muted-foreground">Secured vs Unsecured</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 text-sm">
                    <li>
                      Secured: ₹
                      <span className="font-semibold">
                        {(creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.totalOutstandingBalance?.outstandingBalanceSecured ?? (creditReport?.creditReportData ? 0 : "N/A")).toLocaleString("en-IN")}
                      </span>
                    </li>
                    <li>
                      Unsecured: ₹
                      <span className="font-semibold">
                        {(creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.totalOutstandingBalance?.outstandingBalanceUnSecured ?? (creditReport?.creditReportData ? 0 : "N/A")).toLocaleString("en-IN")}
                      </span>
                    </li>
                    <li>
                      Total: ₹
                      <span className="font-semibold">
                        {(creditReport?.creditReportData?.creditAccount?.creditAccountSummary?.totalOutstandingBalance?.outstandingBalanceAll ?? (creditReport?.creditReportData ? 0 : "N/A")).toLocaleString("en-IN")}
                      </span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* CAPS Inquiries */}
            {!creditReport?.creditReportData?.caps?.capsSummary?.capsLast180Days ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No CAPS Inquiries Available</CardTitle>
                  <CardDescription className="text-muted-foreground">CAPS inquiry data is missing.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <div className="flex flex-col h-full">
                {capsCount > 3 && (
                  <div className="text-sm text-yellow-600 font-medium mb-2">
                    ⚠️ You've had multiple recent credit inquiries. This may impact your score.
                  </div>
                )}
                <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg flex-1">
                  <CardHeader>
                    <CardTitle className="text-primary font-semibold text-xl">CAPS Inquiries</CardTitle>
                    <CardDescription className="text-muted-foreground">Last 180 Days</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold text-primary">
                      {capsCount}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>

          {/* Credit Accounts and CAPS Applications */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {/* Credit Accounts */}
            {!Array.isArray(creditReport?.creditReportData?.creditAccount?.creditAccountDetails) ||
            creditReport?.creditReportData?.creditAccount?.creditAccountDetails.length === 0 ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No Credit Accounts Available</CardTitle>
                  <CardDescription className="text-muted-foreground">No individual loan accounts found.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">Credit Accounts</CardTitle>
                  <CardDescription className="text-muted-foreground">All individual loans</CardDescription>
                </CardHeader>
                <CardContent className="overflow-y-auto max-h-72">
                  <ul className="text-sm space-y-3">
                    {creditReport.creditReportData.creditAccount.creditAccountDetails.map((acc, index) => (
                      <li key={index} className="border-b pb-2">
                        <div className="font-medium">{acc.subscriberName ?? "N/A"}</div>
                        <div className="text-xs text-muted-foreground">
                          Type: {acc.accountType ?? "N/A"} • Opened: {acc.openDate ?? "N/A"} • Balance: ₹{parseInt(acc.currentBalance ?? 0).toLocaleString("en-IN")}
                        </div>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* CAPS Applications */}
            {!Array.isArray(creditReport?.creditReportData?.caps?.capsApplicationDetailsArray) ||
            creditReport?.creditReportData?.caps?.capsApplicationDetailsArray.length === 0 ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No CAPS Applications Available</CardTitle>
                  <CardDescription className="text-muted-foreground">No recent loan inquiries found.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">CAPS Applications</CardTitle>
                  <CardDescription className="text-muted-foreground">Recent loan inquiries</CardDescription>
                </CardHeader>
                <CardContent className="overflow-x-auto max-h-72">
                  <table className="min-w-full text-sm">
                    <thead>
                      <tr className="text-left">
                        <th className="pr-4">Subscriber</th>
                        <th className="pr-4">Enquiry Reason</th>
                        <th className="pr-4">Finance Purpose</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {creditReport.creditReportData.caps.capsApplicationDetailsArray.map((item, index) => (
                        <tr key={index} className="border-t">
                          <td className="pr-4 py-1">{item.SubscriberName ?? "—"}</td>
                          <td className="pr-4 py-1">{item.EnquiryReason ?? "—"}</td>
                          <td className="pr-4 py-1">{item.FinancePurpose ?? "—"}</td>
                          <td className="py-1">{item.DateOfRequest ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Report Metadata */}
          <div className="mt-4">
            {!creditReport?.creditReportData?.creditProfileHeader &&
            !creditReport?.creditReportData?.matchResult &&
            !creditReport?.creditReportData?.userMessage ? (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">No Report Metadata Available</CardTitle>
                  <CardDescription className="text-muted-foreground">Key report attributes are missing.</CardDescription>
                </CardHeader>
              </Card>
            ) : (
              <Card className="h-full p-4 shadow-md border border-gray-200 rounded-lg">
                <CardHeader>
                  <CardTitle className="text-primary font-semibold text-xl">Report Metadata</CardTitle>
                  <CardDescription className="text-muted-foreground">Key report attributes</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 text-sm">
                    <li>
                      Score Date: <span className="font-semibold">{creditReport?.creditReportData?.creditProfileHeader?.reportDate ?? "N/A"}</span>
                    </li>
                    <li>
                      Reported Time: <span className="font-semibold">{creditReport?.creditReportData?.creditProfileHeader?.reportTime ?? "N/A"}</span>
                    </li>
                    <li>
                      Match Status: <span className="font-semibold">{creditReport?.creditReportData?.matchResult?.exactMatch ?? "N/A"}</span>
                    </li>
                    <li>
                      Message: <span className="font-semibold">{creditReport?.creditReportData?.userMessage?.userMessageText ?? "N/A"}</span>
                    </li>
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default Credit;