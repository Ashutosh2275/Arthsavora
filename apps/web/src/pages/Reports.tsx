import React, { useState } from 'react';
import api from '@/lib/axios';
import { FileText, Table, Download, ShieldCheck } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

export default function Reports() {
  const [downloading, setDownloading] = useState<'pdf' | 'excel' | null>(null);

  const downloadReport = async (type: 'pdf' | 'excel') => {
    setDownloading(type);
    try {
      const response = await api.get(`/reports/${type}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Arthsavora_Report.${type === 'excel' ? 'xlsx' : 'pdf'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success(`${type.toUpperCase()} report generated`);
    } catch {
      toast.error('Failed to generate statement. Ensure transactions exist.');
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <header>
        <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
          <FileText className="text-indigo-400" size={24} /> Financial Statements & Export
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Export verified transaction records for tax compliance, personal audit, or external bookkeeping.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* PDF Card */}
        <Card className="flex flex-col justify-between">
          <div>
            <div className="rounded-xl bg-rose-500/10 p-3 text-rose-400 w-fit mb-4">
              <FileText size={24} />
            </div>
            <h3 className="text-lg font-bold text-white">Financial Statement (PDF)</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Standardized statement containing categorized breakdowns, summary metrics, and date-sorted transaction lines. Ideal for accounting archives and tax filings.
            </p>
          </div>
          <Button
            variant="outline"
            className="w-full mt-6 gap-2"
            onClick={() => downloadReport('pdf')}
            isLoading={downloading === 'pdf'}
          >
            <Download size={16} />
            <span>Download PDF</span>
          </Button>
        </Card>

        {/* Excel Card */}
        <Card className="flex flex-col justify-between">
          <div>
            <div className="rounded-xl bg-emerald-500/10 p-3 text-emerald-400 w-fit mb-4">
              <Table size={24} />
            </div>
            <h3 className="text-lg font-bold text-white">Raw Transaction Ledger (Excel)</h3>
            <p className="text-xs text-slate-400 mt-2 leading-relaxed">
              Complete tabular export in `.xlsx` format. Ready for import into Microsoft Excel, Google Sheets, or Tally for deep cash flow modeling.
            </p>
          </div>
          <Button
            variant="outline"
            className="w-full mt-6 gap-2"
            onClick={() => downloadReport('excel')}
            isLoading={downloading === 'excel'}
          >
            <Download size={16} />
            <span>Download Excel</span>
          </Button>
        </Card>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-4 flex items-center gap-3">
        <ShieldCheck className="text-indigo-400 shrink-0" size={20} />
        <p className="text-xs text-slate-400 leading-relaxed">
          All financial reports are streamed directly to your browser memory. Data is not cached in permanent server files, ensuring data privacy and statutory compliance.
        </p>
      </div>
    </div>
  );
}
