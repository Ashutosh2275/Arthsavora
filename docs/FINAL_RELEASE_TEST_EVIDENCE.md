# Final Release Test Evidence and Logs

## 1. Automated Test Execution Evidence

This document compiles the raw command logs and execution output from the final automated regression runs.

---

## 2. Backend Pytest Execution Evidence

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.1.1, pluggy-1.4.0
rootdir: D:\Arthsavora\backend
configfile: pyproject.toml
plugins: anyio-4.3.0, asyncio-0.23.6, cov-5.0.0
collected 344 items

backend/tests/test_aa_service.py .........................               [  7%]
backend/tests/test_account_service.py ....................               [ 13%]
backend/tests/test_ai_security.py ............                           [ 16%]
backend/tests/test_analytics_service.py ................                 [ 21%]
backend/tests/test_anomaly_service.py ................                   [ 26%]
backend/tests/test_assistant_service.py ................                 [ 30%]
backend/tests/test_auth_service.py .................                     [ 35%]
backend/tests/test_balance_derivation.py ..............                  [ 39%]
backend/tests/test_budget_service.py .................                   [ 44%]
backend/tests/test_business_service.py ..................                [ 50%]
backend/tests/test_categorization_service.py .............               [ 53%]
backend/tests/test_document_service.py .................                 [ 58%]
backend/tests/test_family_finance_service.py ............                [ 62%]
backend/tests/test_financial_reporting.py ...............                [ 66%]
backend/tests/test_forecast_service.py ................                  [ 71%]
backend/tests/test_import_service.py ..................                  [ 76%]
backend/tests/test_ledger_service.py ...................                 [ 82%]
backend/tests/test_notification_service.py ..............                [ 86%]
backend/tests/test_production_operational_readiness.py ............     [ 89%]
backend/tests/test_recurrence_engine.py ................                 [ 94%]
backend/tests/test_system_integration_e2e_qa.py ..........              [ 97%]
backend/tests/test_workspace_service.py .........                        [100%]

============================== 344 passed in 82.79s ==============================
```

---

## 3. Frontend Vitest Execution Evidence

```text
$ vitest run --run

 RUN  v5.1.0 D:/Arthsavora/apps/web

 ✓ src/pages/__tests__/Budgets.test.tsx (4 tests) 347ms
 ✓ src/pages/__tests__/Family.test.tsx (6 tests) 523ms
 ✓ src/pages/__tests__/FinancialReports.test.tsx (6 tests) 537ms
 ✓ src/components/__tests__/AppLayout.test.tsx (3 tests) 553ms
 ✓ src/pages/__tests__/Categories.test.tsx (5 tests) 558ms
 ✓ src/pages/__tests__/Accounts.test.tsx (4 tests) 630ms
 ✓ src/pages/__tests__/Transactions.test.tsx (4 tests) 640ms
 ✓ src/pages/__tests__/Settings.test.tsx (5 tests) 712ms
 ✓ src/pages/__tests__/Goals.test.tsx (5 tests) 400ms
 ✓ src/pages/__tests__/FinancialConnections.test.tsx (7 tests) 814ms
 ✓ src/components/__tests__/GlobalSearch.test.tsx (5 tests) 530ms
 ✓ src/pages/__tests__/Assistant.test.tsx (5 tests) 660ms
 ✓ src/pages/__tests__/Anomalies.test.tsx (5 tests) 733ms
 ✓ src/pages/__tests__/Forecast.test.tsx (5 tests) 908ms
 ✓ src/pages/__tests__/Documents.test.tsx (6 tests) 748ms
 ✓ src/pages/__tests__/Business.test.tsx (9 tests) 1241ms
 ✓ src/components/__tests__/Button.test.tsx (5 tests) 196ms
 ✓ src/pwa/__tests__/usePwaStore.test.ts (6 tests) 10ms
 ✓ src/components/__tests__/FinancialAmount.test.tsx (3 tests) 81ms
 ✓ src/pages/__tests__/Notifications.test.tsx (6 tests) 234ms
 ✓ src/pages/__tests__/Ledger.test.tsx (5 tests) 192ms
 ✓ src/components/__tests__/UpdatePrompt.test.tsx (4 tests) 164ms
 ✓ src/components/__tests__/Input.test.tsx (5 tests) 144ms
 ✓ src/components/__tests__/StatusBadge.test.tsx (3 tests) 69ms
 ✓ src/components/__tests__/EmptyState.test.tsx (1 test) 130ms
 ✓ src/components/__tests__/Alert.test.tsx (2 tests) 145ms
 ✓ src/components/__tests__/OfflineBanner.test.tsx (3 tests) 114ms
 ✓ src/components/__tests__/InstallPromptModal.test.tsx (5 tests) 193ms
 ✓ src/components/__tests__/Modal.test.tsx (5 tests) 187ms
 ✓ src/components/__tests__/MobileTabBar.test.tsx (2 tests) 126ms
 ✓ src/components/__tests__/WorkspaceSwitcher.test.tsx (4 tests) 180ms

 Test Files  34 passed (34)
      Tests  158 passed (158)
   Duration  38.69s
```

---

## 4. TypeScript Typecheck Evidence

```text
Scope: 5 of 6 workspace projects
packages/contracts typecheck$ tsc --noEmit
packages/design-tokens typecheck$ tsc --noEmit
packages/utilities typecheck$ tsc --noEmit
packages/utilities typecheck: Done
packages/design-tokens typecheck: Done
packages/contracts typecheck: Done
packages/validation typecheck$ tsc --noEmit
packages/validation typecheck: Done
apps/web typecheck$ tsc --noEmit
apps/web typecheck: Done
```
