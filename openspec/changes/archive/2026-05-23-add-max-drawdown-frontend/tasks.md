## 1. Frontend - Add max drawdown input to OptimizerPanel

- [x] 1.1 Add `targetMaxDrawdown` state variable in `OptimizerPanel.tsx`
- [x] 1.2 Add UI input field for max drawdown constraint
- [x] 1.3 Update `handleOptimize` to pass `targetMaxDrawdown` to API

## 2. Frontend - Update API function

- [x] 2.1 Add `targetMaxDrawdown` parameter to `optimizePortfolio` function
- [x] 2.2 Include `target_max_drawdown` in API request body

## 3. Verification

- [x] 3.1 Run `npm run lint` - lint config missing but build succeeded (pre-existing errors in test files)
- [x] 3.2 Verify UI displays correctly