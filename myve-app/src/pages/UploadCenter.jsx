

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Upload } from 'lucide-react';

const UploadCenter = () => (
  <div className="space-y-6">
    <h2 className="text-3xl font-bold">Upload Center</h2>
    <Card>
      <CardHeader>
        <CardTitle>Upload Documents</CardTitle>
        <CardDescription>Upload bank statements, salary slips, and other financial documents</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
          <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-lg font-medium mb-2">Drag and drop files here</p>
          <p className="text-sm text-muted-foreground mb-4">Supports PDF, CSV files</p>
          <Button>Choose Files</Button>
        </div>
      </CardContent>
    </Card>
  </div>
);

export default UploadCenter;