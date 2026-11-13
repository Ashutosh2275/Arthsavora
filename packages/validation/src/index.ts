import { z } from 'zod';

export const LoginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters long'),
});

export const SignupSchema = z.object({
  full_name: z.string().min(2, 'Full name must be at least 2 characters long'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters long'),
});

export const ExpenseCreateSchema = z.object({
  amount: z.number().positive('Amount must be greater than zero'),
  description: z.string().min(1, 'Description is required').max(255),
  category: z.enum([
    'Food',
    'Travel',
    'Shopping',
    'Bills',
    'Entertainment',
    'Health',
    'Housing',
    'Education',
    'Investment',
    'Business',
    'Uncategorized',
  ]).default('Shopping'),
  date: z.string().optional(),
  source: z.enum(['MANUAL', 'SMS', 'OCR', 'BANK_FEED', 'IMPORT']).default('MANUAL'),
});

export const BudgetCreateSchema = z.object({
  category: z.string().min(1, 'Category is required'),
  limit: z.number().positive('Monthly limit must be greater than zero'),
});

export const GoalCreateSchema = z.object({
  name: z.string().min(1, 'Goal name is required').max(100),
  target_amount: z.number().positive('Target amount must be greater than zero'),
  current_amount: z.number().min(0, 'Current amount cannot be negative').default(0),
  category: z.string().default('Savings'),
  deadline: z.string().optional().nullable(),
});

export const SmsParseSchema = z.object({
  text: z.string().min(5, 'SMS text is too short to parse'),
});

export const ChatMessageSchema = z.object({
  message: z.string().min(1, 'Message cannot be empty'),
});

export type LoginInput = z.infer<typeof LoginSchema>;
export type SignupInput = z.infer<typeof SignupSchema>;
export type ExpenseCreateInput = z.infer<typeof ExpenseCreateSchema>;
export type BudgetCreateInput = z.infer<typeof BudgetCreateSchema>;
export type GoalCreateInput = z.infer<typeof GoalCreateSchema>;
