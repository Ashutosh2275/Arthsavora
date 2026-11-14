import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Categories from '../Categories';
import useCategoryStore from '@/store/useCategoryStore';

vi.mock('@/store/useCategoryStore');

const mockCategoryTree = [
  {
    id: 'cat-1',
    name: 'Food & Dining',
    slug: 'food-dining',
    category_type: 'expense',
    parent_id: null,
    workspace_id: null,
    is_system: true,
    is_active: true,
    color: '#EF4444',
    icon: 'utensils',
    children: [
      {
        id: 'cat-1-1',
        name: 'Restaurants',
        slug: 'restaurants',
        category_type: 'expense',
        parent_id: 'cat-1',
        workspace_id: null,
        is_system: true,
        is_active: true,
        children: [],
      },
    ],
  },
  {
    id: 'cat-2',
    name: 'Income',
    slug: 'income',
    category_type: 'income',
    parent_id: null,
    workspace_id: null,
    is_system: true,
    is_active: true,
    color: '#10B981',
    icon: 'briefcase',
    children: [],
  },
];

const mockRules = [
  {
    id: 'rule-1',
    workspace_id: 'ws-1',
    name: 'Swiggy Food Rule',
    priority: 10,
    is_enabled: true,
    suggested_category_id: 'cat-1-1',
    suggested_category_name: 'Restaurants',
    rule_scope: 'workspace',
    conditions: { description_contains: ['SWIGGY'] },
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
];

const mockMerchants = [
  {
    id: 'm-1',
    canonical_name: 'Swiggy',
    merchant_type: 'food_delivery',
    default_category_id: 'cat-1-1',
    aliases: [
      { id: 'a-1', alias: 'SWIGGY' },
      { id: 'a-2', alias: 'BUNDL TECHNOLOGIES' },
    ],
  },
  {
    id: 'm-2',
    canonical_name: 'Uber',
    merchant_type: 'transportation',
    default_category_id: null,
    aliases: [{ id: 'a-3', alias: 'UBER INDIA' }],
  },
];

describe('Categories and Intelligence Page', () => {
  const fetchCategoryTree = vi.fn();
  const fetchCategories = vi.fn();
  const fetchRules = vi.fn();
  const fetchMerchants = vi.fn();
  const createCategory = vi.fn();
  const deleteCategory = vi.fn();
  const createRule = vi.fn();
  const deleteRule = vi.fn();
  const previewSuggestion = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    previewSuggestion.mockResolvedValue({
      suggested_category_id: 'cat-1-1',
      suggested_category_name: 'Food & Dining / Restaurants',
      confidence_score: 0.95,
      confidence_band: 'high',
      method: 'rule',
      explanation: 'Matched rule "Swiggy Food Rule"',
      extracted_merchant: 'Swiggy',
      payment_channel: 'upi',
    });

    (useCategoryStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      categoryTree: mockCategoryTree,
      categories: mockCategoryTree,
      rules: mockRules,
      merchants: mockMerchants,
      loading: false,
      error: null,
      fetchCategoryTree,
      fetchCategories,
      fetchRules,
      fetchMerchants,
      createCategory,
      deleteCategory,
      createRule,
      deleteRule,
      previewSuggestion,
    });
  });

  it('renders page header and tabs correctly', () => {
    render(<Categories />);
    expect(screen.getByRole('heading', { level: 1, name: /Category & Merchant Intelligence/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Category Taxonomy/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Classification Rules/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Recognized Merchants/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Intelligence Sandbox/i })).toBeInTheDocument();
  });

  it('renders category taxonomy tree tab by default', () => {
    render(<Categories />);
    expect(screen.getByText('Food & Dining')).toBeInTheDocument();
    expect(screen.getByText('Income')).toBeInTheDocument();
    expect(screen.getByText('1 subcategories')).toBeInTheDocument();
    expect(fetchCategoryTree).toHaveBeenCalledTimes(1);
    expect(fetchRules).toHaveBeenCalledTimes(1);
    expect(fetchMerchants).toHaveBeenCalledTimes(1);
  });

  it('switches to classification rules tab', () => {
    render(<Categories />);
    fireEvent.click(screen.getByRole('button', { name: /Classification Rules/i }));
    expect(screen.getByText('Swiggy Food Rule')).toBeInTheDocument();
    expect(screen.getByText('Priority 10')).toBeInTheDocument();
    expect(screen.getByText('Enabled')).toBeInTheDocument();
  });

  it('switches to recognized merchants tab', () => {
    render(<Categories />);
    fireEvent.click(screen.getByRole('button', { name: /Recognized Merchants/i }));
    expect(screen.getByText('Swiggy')).toBeInTheDocument();
    expect(screen.getByText('BUNDL TECHNOLOGIES')).toBeInTheDocument();
    expect(screen.getByText('Uber')).toBeInTheDocument();
    expect(screen.getByText('UBER INDIA')).toBeInTheDocument();
  });

  it('switches to intelligence sandbox and executes preview', async () => {
    render(<Categories />);
    fireEvent.click(screen.getByRole('button', { name: /Intelligence Sandbox/i }));

    expect(screen.getByPlaceholderText(/UPI\/SWIGGY/i)).toBeInTheDocument();
    const evalBtn = screen.getByRole('button', { name: /Evaluate/i });
    fireEvent.click(evalBtn);

    await waitFor(() => {
      expect(previewSuggestion).toHaveBeenCalledWith('UPI/SWIGGY/1234567890/PAYMENT');
      expect(screen.getByText('Food & Dining / Restaurants')).toBeInTheDocument();
      expect(screen.getByText(/HIGH CONFIDENCE \(95%\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Matched rule "Swiggy Food Rule"/i)).toBeInTheDocument();
    });
  });
});
