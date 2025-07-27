

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { FileText, BarChart3, MessageCircle, Download } from 'lucide-react';

const Reports = () => (
  <div className="space-y-6">
    <h2 className="text-3xl font-bold">Reports</h2>
    <Card>
      <CardHeader>
        <CardTitle>Export Center</CardTitle>
        <CardDescription>Generate and download financial reports</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Button variant="outline" className="h-20 flex-col">
            <FileText className="w-6 h-6 mb-2" />
            Financial Health Report
          </Button>
          <Button variant="outline" className="h-20 flex-col">
            <BarChart3 className="w-6 h-6 mb-2" />
            Asset Allocation Report
          </Button>
          <Button variant="outline" className="h-20 flex-col">
            <MessageCircle className="w-6 h-6 mb-2" />
            Chat Transcript
          </Button>
          <Button variant="outline" className="h-20 flex-col">
            <Download className="w-6 h-6 mb-2" />
            Data Export
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
);

export default Reports;