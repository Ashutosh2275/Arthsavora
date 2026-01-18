import React from 'react';
import api from '../api/axios';
import { FileText, Table, Download, ShieldCheck, PieChart } from 'lucide-react';

export default function Reports() {
  
  const downloadReport = async (type) => {
    try {
      const response = await api.get(`/reports/${type}`, {
        responseType: 'blob', // Critical for file downloads
      });
      
      // Create a local URL for the binary data
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Arthsavora_Report.${type === 'excel' ? 'xlsx' : 'pdf'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      alert("Failed to generate report. Ensure you have expenses logged.");
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white p-4 md:p-10">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12">
          <h2 className="text-3xl font-bold flex items-center gap-3">
            <FileText className="text-indigo-400" /> Export Statements
          </h2>
          <p className="text-slate-500 mt-2">Generate official financial logs for taxes or personal backup.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* PDF Card */}
          <div className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2.5rem] hover:border-indigo-500/30 transition-all group">
            <div className="bg-red-500/10 text-red-400 p-4 rounded-2xl w-fit mb-6 group-hover:scale-110 transition-transform">
              <FileText size={32} />
            </div>
            <h3 className="text-xl font-bold mb-2">Professional PDF</h3>
            <p className="text-slate-400 text-sm mb-8 leading-relaxed">
              Detailed summary of transactions with category headers and total expenditure. Best for printing or sharing.
            </p>
            <button 
              onClick={() => downloadReport('pdf')}
              className="w-full bg-slate-800 hover:bg-indigo-600 text-white font-bold py-4 rounded-2xl flex items-center justify-center gap-2 transition-all shadow-lg"
            >
              <Download size={18} /> Download PDF
            </button>
          </div>

          {/* Excel Card */}
          <div className="bg-slate-900/50 border border-slate-800 p-8 rounded-[2.5rem] hover:border-emerald-500/30 transition-all group">
            <div className="bg-emerald-500/10 text-emerald-400 p-4 rounded-2xl w-fit mb-6 group-hover:scale-110 transition-transform">
              <Table size={32} />
            </div>
            <h3 className="text-xl font-bold mb-2">Raw Data (Excel)</h3>
            <p className="text-slate-400 text-sm mb-8 leading-relaxed">
              Full transaction log in .xlsx format. Perfect for deep analysis in Excel, Google Sheets, or Tally.
            </p>
            <button 
              onClick={() => downloadReport('excel')}
              className="w-full bg-slate-800 hover:bg-emerald-600 text-white font-bold py-4 rounded-2xl flex items-center justify-center gap-2 transition-all shadow-lg"
            >
              <Download size={18} /> Download Excel
            </button>
          </div>
        </div>

        {/* Security Footer */}
        <div className="mt-12 p-6 border border-slate-800/50 rounded-3xl flex items-center gap-4 bg-slate-900/20">
          <ShieldCheck className="text-indigo-400 shrink-0" size={24} />
          <p className="text-xs text-slate-500 leading-relaxed">
            All generated reports are encrypted and processed in real-time. Arthsavora does not store your generated files on its servers; they are streamed directly to your device to ensure maximum privacy.
          </p>
        </div>
      </div>
    </div>
  );
}