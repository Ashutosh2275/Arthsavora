import React, { useEffect, useState } from 'react';
import useCategoryStore from '@/store/useCategoryStore';
import {
  FolderTree,
  Plus,
  Sparkles,
  Search,
  Tag,
  ShieldCheck,
  Sliders,
  Trash2,
  Edit2,
  ChevronRight,
  ChevronDown,
  Building2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Modal } from '@/components/ui/modal';
import { toast } from 'sonner';
import type { CategoryCreateRequest, RuleCreateRequest } from '@arthsavora/contracts';

export default function Categories() {
  const {
    categories,
    categoryTree,
    rules,
    merchants,
    loading,
    fetchCategories,
    fetchCategoryTree,
    fetchRules,
    fetchMerchants,
    createCategory,
    deleteCategory,
    createRule,
    deleteRule,
    previewSuggestion,
  } = useCategoryStore();

  const [activeTab, setActiveTab] = useState<'taxonomy' | 'rules' | 'merchants' | 'preview'>('taxonomy');
  const [search, setSearch] = useState('');
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({});

  // Modals
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [isRuleModalOpen, setIsRuleModalOpen] = useState(false);

  // Forms
  const [categoryForm, setCategoryForm] = useState<CategoryCreateRequest>({
    name: '',
    category_type: 'expense',
    parent_id: null,
    workspace_type: 'all',
    icon: 'tag',
    color: '#3B82F6',
    display_order: 0,
  });

  const [ruleForm, setRuleForm] = useState<{
    name: string;
    keyword: string;
    direction: string;
    suggested_category_id: string;
    priority: number;
  }>({
    name: '',
    keyword: '',
    direction: 'outflow',
    suggested_category_id: '',
    priority: 150,
  });

  // Preview form
  const [previewText, setPreviewText] = useState('UPI/SWIGGY/1234567890/PAYMENT');
  const [previewResult, setPreviewResult] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    fetchCategoryTree();
    fetchCategories();
    fetchRules();
    fetchMerchants();
  }, []);

  const toggleNode = (id: string) => {
    setExpandedNodes((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryForm.name.trim()) {
      toast.error('Category name is required.');
      return;
    }
    try {
      await createCategory(categoryForm);
      toast.success('Category created successfully.');
      setIsCategoryModalOpen(false);
      fetchCategoryTree();
      fetchCategories();
      setCategoryForm({
        name: '',
        category_type: 'expense',
        parent_id: null,
        workspace_type: 'all',
        icon: 'tag',
        color: '#3B82F6',
        display_order: 0,
      });
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to create category.');
    }
  };

  const handleDeleteCategory = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this custom category?')) return;
    try {
      await deleteCategory(id);
      toast.success('Category deleted.');
      fetchCategoryTree();
      fetchCategories();
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Cannot delete category.');
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleForm.name.trim() || !ruleForm.keyword.trim() || !ruleForm.suggested_category_id) {
      toast.error('All fields are required to create a rule.');
      return;
    }
    try {
      await createRule({
        name: ruleForm.name,
        conditions: {
          description_contains: [ruleForm.keyword.trim()],
          direction: ruleForm.direction,
        },
        suggested_category_id: ruleForm.suggested_category_id,
        priority: ruleForm.priority,
      });
      toast.success('Classification rule created.');
      setIsRuleModalOpen(false);
      fetchRules();
      setRuleForm({
        name: '',
        keyword: '',
        direction: 'outflow',
        suggested_category_id: '',
        priority: 150,
      });
    } catch (err: any) {
      toast.error(err.response?.data?.message || 'Failed to create rule.');
    }
  };

  const handleDeleteRule = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this rule?')) return;
    try {
      await deleteRule(id);
      toast.success('Rule deleted.');
    } catch (err: any) {
      toast.error('Failed to delete rule.');
    }
  };

  const handleTestPreview = async () => {
    if (!previewText.trim()) return;
    setPreviewLoading(true);
    try {
      const res = await previewSuggestion(previewText);
      setPreviewResult(res);
    } catch (err: any) {
      toast.error('Preview evaluation failed.');
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Category & Merchant Intelligence</h1>
          <p className="text-sm text-muted-foreground">
            Hierarchical financial taxonomy, merchant aliases, deterministic rules, and AI classification.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {activeTab === 'taxonomy' && (
            <Button onClick={() => setIsCategoryModalOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" /> Add Category
            </Button>
          )}
          {activeTab === 'rules' && (
            <Button onClick={() => setIsRuleModalOpen(true)} className="gap-2">
              <Plus className="h-4 w-4" /> Add Rule
            </Button>
          )}
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex gap-2 border-b border-border pb-2">
        <button
          onClick={() => setActiveTab('taxonomy')}
          className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'taxonomy'
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-muted-foreground hover:bg-muted/50'
          }`}
        >
          <FolderTree className="h-4 w-4" /> Category Taxonomy
        </button>
        <button
          onClick={() => setActiveTab('rules')}
          className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'rules'
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-muted-foreground hover:bg-muted/50'
          }`}
        >
          <Sliders className="h-4 w-4" /> Classification Rules ({rules.length})
        </button>
        <button
          onClick={() => setActiveTab('merchants')}
          className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'merchants'
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-muted-foreground hover:bg-muted/50'
          }`}
        >
          <Building2 className="h-4 w-4" /> Recognized Merchants ({merchants.length})
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
            activeTab === 'preview'
              ? 'bg-primary/10 text-primary font-semibold'
              : 'text-muted-foreground hover:bg-muted/50'
          }`}
        >
          <Sparkles className="h-4 w-4" /> Intelligence Sandbox
        </button>
      </div>

      {/* Tab 1: Category Taxonomy */}
      {activeTab === 'taxonomy' && (
        <div className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Category Hierarchy</h2>
              <span className="text-xs text-muted-foreground">Universal system categories + Workspace custom categories</span>
            </div>

            <div className="divide-y divide-border">
              {categoryTree.map((root) => {
                const isExpanded = expandedNodes[root.id] ?? true;
                return (
                  <div key={root.id} className="py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 cursor-pointer" onClick={() => toggleNode(root.id)}>
                        {root.children && root.children.length > 0 ? (
                          isExpanded ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          )
                        ) : (
                          <div className="w-4" />
                        )}
                        <span
                          className="h-3 w-3 rounded-full"
                          style={{ backgroundColor: root.color || '#94A3B8' }}
                        />
                        <span className="font-medium text-foreground">{root.name}</span>
                        <Badge variant="neutral" className="text-xs uppercase">
                          {root.category_type}
                        </Badge>
                        {root.is_system && (
                          <Badge variant="brand" className="text-[10px]">
                            System
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {root.children ? `${root.children.length} subcategories` : '0 subcategories'}
                        </span>
                        {!root.is_system && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDeleteCategory(root.id)}
                            className="text-destructive h-7 w-7 p-0"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Subcategories list */}
                    {isExpanded && root.children && root.children.length > 0 && (
                      <div className="mt-2 ml-6 space-y-1 pl-4 border-l-2 border-muted">
                        {root.children.map((sub) => (
                          <div key={sub.id} className="flex items-center justify-between py-1.5 text-sm">
                            <div className="flex items-center gap-2">
                              <span className="text-foreground">{sub.name}</span>
                              <span className="text-xs text-muted-foreground font-mono">({sub.slug})</span>
                              {sub.is_system ? (
                                <Badge variant="brand" className="text-[10px]">
                                  System
                                </Badge>
                              ) : (
                                <Badge variant="neutral" className="text-[10px] text-primary">
                                  Custom
                                </Badge>
                              )}
                            </div>
                            {!sub.is_system && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteCategory(sub.id)}
                                className="text-destructive h-6 w-6 p-0"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* Tab 2: Classification Rules */}
      {activeTab === 'rules' && (
        <div className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Deterministic Rules</h2>
                <p className="text-xs text-muted-foreground">
                  Evaluated in priority order before ML prediction. Guarantees deterministic classification.
                </p>
              </div>
            </div>

            {rules.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Sliders className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No custom rules created yet. Click "Add Rule" to define keyword matches.</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {rules.map((rule) => (
                  <div key={rule.id} className="py-3 flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-foreground">{rule.name}</span>
                        <Badge variant="neutral" className="text-xs">
                          Priority {rule.priority}
                        </Badge>
                        <Badge variant={rule.is_enabled ? 'income' : 'neutral'} className="text-xs">
                          {rule.is_enabled ? 'Enabled' : 'Disabled'}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground flex items-center gap-3">
                        <span>
                          Category: <strong className="text-foreground">{rule.suggested_category_name || 'Assigned'}</strong>
                        </span>
                        <span>Conditions: {JSON.stringify(rule.conditions)}</span>
                      </div>
                    </div>
                    <div>
                      {rule.workspace_id && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteRule(rule.id)}
                          className="text-destructive h-8 w-8 p-0"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab 3: Recognized Merchants */}
      {activeTab === 'merchants' && (
        <div className="space-y-4">
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Known Merchants & Aliases</h2>
                <p className="text-xs text-muted-foreground">
                  Verified Indian merchants automatically mapped to categories with high confidence.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {merchants.map((m) => (
                <div key={m.id} className="p-3 border border-border rounded-lg space-y-2 bg-card">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-foreground text-sm">{m.canonical_name}</span>
                    <Badge variant="info" className="text-[10px]">
                      {m.merchant_type}
                    </Badge>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {m.aliases.map((a) => (
                      <span
                        key={a.id}
                        className="text-[11px] px-1.5 py-0.5 bg-muted rounded font-mono text-muted-foreground"
                      >
                        {a.alias}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Tab 4: Intelligence Sandbox */}
      {activeTab === 'preview' && (
        <div className="space-y-4">
          <Card className="p-4 space-y-4">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Live Intelligence Sandbox</h2>
              <p className="text-xs text-muted-foreground">
                Enter any raw bank narration, UPI string, or merchant description to test the hybrid classifier in real-time.
              </p>
            </div>

            <div className="flex gap-2">
              <Input
                value={previewText}
                onChange={(e) => setPreviewText(e.target.value)}
                placeholder="e.g. UPI/SWIGGY/1234567890/UPI-PAY or POS 4402 STARBUCKS BANGALORE"
                className="flex-1 font-mono text-sm"
              />
              <Button onClick={handleTestPreview} disabled={previewLoading} className="gap-2">
                <Sparkles className="h-4 w-4" /> Evaluate
              </Button>
            </div>

            {previewResult && (
              <div className="mt-4 p-4 border border-border rounded-lg bg-muted/20 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground uppercase font-semibold">Suggested Category</span>
                    <h3 className="text-lg font-bold text-foreground">{previewResult.suggested_category_name}</h3>
                  </div>
                  <div className="text-right">
                    <Badge
                      variant={
                        previewResult.confidence_band === 'high'
                          ? 'income'
                          : previewResult.confidence_band === 'medium'
                          ? 'brand'
                          : previewResult.confidence_band === 'low'
                          ? 'warning'
                          : 'neutral'
                      }
                      className="text-xs"
                    >
                      {previewResult.confidence_band.toUpperCase()} CONFIDENCE (
                      {Math.round(previewResult.confidence_score * 100)}%)
                    </Badge>
                    <p className="text-[11px] text-muted-foreground mt-1">Method: {previewResult.method}</p>
                  </div>
                </div>

                <div className="text-sm text-foreground bg-card p-3 rounded border border-border">
                  <p className="text-xs text-muted-foreground mb-1 font-semibold">Explanation</p>
                  <p>{previewResult.explanation}</p>
                </div>

                <div className="grid grid-cols-3 gap-2 text-xs text-muted-foreground pt-2">
                  <div>
                    Normalized Description:{' '}
                    <strong className="text-foreground">{previewResult.normalized_description}</strong>
                  </div>
                  <div>
                    Merchant Candidate:{' '}
                    <strong className="text-foreground">{previewResult.merchant_candidate || 'None'}</strong>
                  </div>
                  <div>
                    Payment Channel: <strong className="text-foreground">{previewResult.payment_channel}</strong>
                  </div>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Add Category Modal */}
      <Modal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        title="Add Custom Financial Category"
      >
        <form onSubmit={handleCreateCategory} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground">Category Name</label>
            <Input
              value={categoryForm.name}
              onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
              placeholder="e.g. Cloud Hosting"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground">Category Type</label>
            <select
              value={categoryForm.category_type}
              onChange={(e) => setCategoryForm({ ...categoryForm, category_type: e.target.value })}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="expense">Expense</option>
              <option value="income">Income</option>
              <option value="transfer">Transfer</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground">Parent Category (Optional)</label>
            <select
              value={categoryForm.parent_id || ''}
              onChange={(e) =>
                setCategoryForm({
                  ...categoryForm,
                  parent_id: e.target.value ? (e.target.value as any) : null,
                })
              }
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
            >
              <option value="">No Parent (Root Category)</option>
              {categoryTree.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsCategoryModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              Create Category
            </Button>
          </div>
        </form>
      </Modal>

      {/* Add Rule Modal */}
      <Modal
        isOpen={isRuleModalOpen}
        onClose={() => setIsRuleModalOpen(false)}
        title="Create Classification Rule"
      >
        <form onSubmit={handleCreateRule} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-muted-foreground">Rule Name</label>
            <Input
              value={ruleForm.name}
              onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })}
              placeholder="e.g. AWS Cloud Expenses"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground">If Description Contains Keyword</label>
            <Input
              value={ruleForm.keyword}
              onChange={(e) => setRuleForm({ ...ruleForm, keyword: e.target.value })}
              placeholder="e.g. AMAZON WEB SERVICES or AWS"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted-foreground">Then Assign Category</label>
            <select
              value={ruleForm.suggested_category_id}
              onChange={(e) => setRuleForm({ ...ruleForm, suggested_category_id: e.target.value })}
              className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-md text-sm"
              required
            >
              <option value="">Select a category...</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.category_type})
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsRuleModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading}>
              Save Rule
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
