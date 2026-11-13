import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { captureException } from '@/lib/observability';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorId?: string;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    const errorId = captureException(error, {
      componentStack: errorInfo.componentStack || undefined,
    });
    this.setState({ errorId });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          aria-live="assertive"
          className="flex min-h-[400px] flex-col items-center justify-center p-8 text-center"
        >
          <div className="mb-4 rounded-2xl bg-rose-500/10 p-4 text-rose-400">
            <AlertTriangle className="h-9 w-9" aria-hidden="true" />
          </div>
          <h3 className="text-xl font-bold text-white">Something went wrong</h3>
          <p className="mt-2 max-w-md text-sm text-slate-400">
            An unexpected error occurred while rendering this financial view.
          </p>
          {this.state.errorId && (
            <p className="mt-1 font-mono text-xs text-slate-500">
              Reference ID: {this.state.errorId}
            </p>
          )}
          <Button
            variant="outline"
            size="sm"
            className="mt-6 gap-2"
            onClick={() => window.location.reload()}
          >
            <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Reload Application</span>
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
