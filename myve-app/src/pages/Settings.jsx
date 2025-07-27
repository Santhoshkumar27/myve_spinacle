import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { useMcp } from '../context/McpContext';

const SettingsPage = () => {
  const { isConnected, setIsConnected, tools, setTools } = useMcp();

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold">Settings</h2>
      <Card>
        <CardHeader>
          <CardTitle>Account Settings</CardTitle>
          <CardDescription>Manage your account preferences and data sources</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {tools.length > 0 && (
              <div className="mt-4">
                <h4 className="font-medium">Available MCP Tools</h4>
                <ul className="list-disc ml-6 mt-2 text-sm text-muted-foreground">
                  {tools.map((tool, idx) => (
                    <li key={idx}>{tool}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Notifications</h4>
                <p className="text-sm text-muted-foreground">Manage notification preferences</p>
              </div>
              <Button variant="outline">Configure</Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">Data Privacy</h4>
                <p className="text-sm text-muted-foreground">Control your data storage preferences</p>
              </div>
              <Button variant="outline">Manage</Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPage;