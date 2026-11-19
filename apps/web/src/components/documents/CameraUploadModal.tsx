import React, { useState, useRef } from 'react';
import { Camera, Upload, X, CheckCircle2, AlertCircle, FileText, Image as ImageIcon, Loader2 } from 'lucide-react';
import { useDocumentStore } from '@/store/useDocumentStore';
import { useWorkspaceStore } from '@/store/useWorkspaceStore';
import { Button } from '@/components/ui/button';

interface CameraUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (documentId: string) => void;
}

export const CameraUploadModal: React.FC<CameraUploadModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [docType, setDocType] = useState<string>('receipt');
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [uploadStep, setUploadStep] = useState<'idle' | 'uploading' | 'processing' | 'done'>('idle');

  const cameraInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { uploadDocument } = useDocumentStore();
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size exceeds the 10MB maximum limit.');
      return;
    }

    setUploadError(null);
    setSelectedFile(file);

    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => {
        setPreviewUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setPreviewUrl(null);
    }
  };

  const handleUploadAndProcess = async () => {
    if (!selectedFile) return;

    setUploadError(null);
    setUploadStep('uploading');

    try {
      const doc = await uploadDocument(
        selectedFile,
        activeWorkspace?.id,
        docType,
        true // autoProcess
      );

      setUploadStep('done');
      if (onSuccess) {
        onSuccess(doc.id);
      }
      setTimeout(() => {
        handleClose();
      }, 1200);
    } catch (err: any) {
      setUploadError(err.response?.data?.message || err.message || 'Failed to upload document');
      setUploadStep('idle');
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadError(null);
    setUploadStep('idle');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="camera-upload-title"
        className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl space-y-5 animate-in zoom-in-95"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Camera size={20} />
            </div>
            <div>
              <h3 id="camera-upload-title" className="text-base font-bold text-white">
                Scan Receipt or Document
              </h3>
              <p className="text-xs text-slate-400">Mobile Camera &amp; File Ingestion</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {uploadError && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle size={15} className="shrink-0 text-rose-400" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Hidden File Inputs */}
        {/* Native camera capture */}
        <input
          ref={cameraInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={handleFileChange}
        />
        {/* Standard file picker */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {uploadStep === 'uploading' ? (
          <div className="py-12 text-center space-y-3">
            <Loader2 size={36} className="text-indigo-400 animate-spin mx-auto" />
            <h4 className="text-sm font-semibold text-white">Uploading &amp; Extracting Fields...</h4>
            <p className="text-xs text-slate-400">
              Encrypting document and initiating Indian tax invoice OCR parsing.
            </p>
          </div>
        ) : uploadStep === 'done' ? (
          <div className="py-10 text-center space-y-2">
            <CheckCircle2 size={40} className="text-emerald-400 mx-auto animate-bounce" />
            <h4 className="text-sm font-semibold text-white">Document Processed!</h4>
            <p className="text-xs text-slate-400">
              Fields extracted. Ready for your review and explicit ledger confirmation.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Capture Buttons */}
            {!selectedFile ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => cameraInputRef.current?.click()}
                  className="flex flex-col items-center justify-center p-6 rounded-xl border border-slate-700 bg-slate-950/60 hover:bg-slate-800/80 hover:border-indigo-500/50 transition-all group"
                >
                  <div className="w-12 h-12 rounded-full bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
                    <Camera size={24} />
                  </div>
                  <span className="text-sm font-medium text-white">Use Camera</span>
                  <span className="text-[11px] text-slate-400 mt-0.5">Snap receipt directly</span>
                </button>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex flex-col items-center justify-center p-6 rounded-xl border border-slate-700 bg-slate-950/60 hover:bg-slate-800/80 hover:border-indigo-500/50 transition-all group"
                >
                  <div className="w-12 h-12 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
                    <Upload size={24} />
                  </div>
                  <span className="text-sm font-medium text-white">Choose File</span>
                  <span className="text-[11px] text-slate-400 mt-0.5">Image or PDF (Max 10MB)</span>
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Preview Box */}
                <div className="rounded-xl border border-slate-700 bg-slate-950 p-3 flex items-center gap-3">
                  {previewUrl ? (
                    <img
                      src={previewUrl}
                      alt="Receipt preview"
                      className="w-16 h-16 object-cover rounded-lg border border-slate-800 shrink-0"
                    />
                  ) : (
                    <div className="w-16 h-16 rounded-lg bg-slate-800 flex items-center justify-center text-slate-400 shrink-0">
                      <FileText size={24} />
                    </div>
                  )}

                  <div className="min-w-0 flex-1">
                    <h5 className="text-xs font-semibold text-white truncate">{selectedFile.name}</h5>
                    <p className="text-[11px] text-slate-400">
                      {(selectedFile.size / 1024).toFixed(1)} KB &bull; {selectedFile.type || 'Document'}
                    </p>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        setPreviewUrl(null);
                      }}
                      className="text-[11px] text-rose-400 hover:text-rose-300 mt-1 inline-block"
                    >
                      Change file
                    </button>
                  </div>
                </div>

                {/* Document Type Selector */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Document Type</label>
                  <select
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                    className="w-full text-xs rounded-lg bg-slate-950 border border-slate-700 px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="receipt">Retail / Restaurant Receipt</option>
                    <option value="invoice">B2B Tax Invoice (GSTIN)</option>
                    <option value="utility_bill">Electricity / Water / Broadband Bill</option>
                    <option value="bank_statement">Bank / Card Statement Page</option>
                  </select>
                </div>

                <div className="rounded-lg bg-slate-950/80 border border-slate-800 p-3 text-[11px] text-slate-400">
                  <span className="font-semibold text-slate-300 block mb-0.5">Verification Integrity Policy:</span>
                  Extracted values will be staged as untrusted data. You will have full opportunity to correct line items, merchant, and amounts before posting to the ledger.
                </div>
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800/60">
          <Button variant="ghost" size="sm" onClick={handleClose} className="text-xs">
            Cancel
          </Button>
          {selectedFile && uploadStep === 'idle' && (
            <Button
              variant="primary"
              size="sm"
              onClick={handleUploadAndProcess}
              className="text-xs bg-indigo-600 hover:bg-indigo-500"
            >
              Upload &amp; Extract
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
