# SmartCart Retail Analytics Assistant — Technical Report

**Interview Assignment Completion Report**  
**Date:** November 28, 2025  
**Stack:** Flask, SQLAlchemy, Pandas/NumPy, mlxtend (Apriori), Flask-WTF, Bootstrap templates  

---

## 1. Executive Summary

Built a Flask-based retail analytics assistant that ingests CSV receipts, validates schemas, suggests thresholds, and generates contextual market-basket rules. The system supports OTP-secured login, first-time store setup, upload tracking, configurable analytics thresholds, KPI dashboards, and an authenticated JSON API for recommendations and chart data. A sample dataset (`datasets/sample_multi_item_baskets.csv`) with **500 orders, 1,184 rows, 15 products, ~2.4 items/order** validates the end-to-end flow with budget percentiles (**p33 ≈ 337**, **p66 ≈ 433**) and realistic shopper contexts (age, time-of-day, occasion).

---

## 2. Approach

### 2.1 Data Ingestion & Validation
- Accepts two schemas: `(order_id, product_id, product_name, …)` or `(transaction_id, product_name, …)` with automatic normalization to `order_id` + hashed `product_id`.
- Cleans numeric columns (fills nulls), trims string columns, and guards against empty/unknown values for downstream stability.
- Persists uploads in `uploads/` with `DataUpload` records capturing size, row counts, and threshold metadata.

### 2.2 Threshold Suggestion & Configuration
- `ThresholdConfigurator` analyzes basket size, spend distribution, demographics, and completeness to compute a quality score and propose:
  - Budget tiers via spend percentiles (defaults to 25/75 if absent)
  - Apriori thresholds (`min_support`, `min_confidence`, `min_lift`) tuned to dataset volume
  - Basket-size cutoffs and age-group boundaries
- `ThresholdHandler` transforms UI form inputs into canonical configs and emits recommendation messages (e.g., warn when transactions < 50).

### 2.3 Analytics Engine
- `RetailAnalyticsEngine` builds enriched transactions with budget segment, basket size, time-of-day, day-of-week, and age group, then runs Apriori + `association_rules`.
- Adaptive thresholds tighten/loosen based on transaction count; rules stored as `AssociationRule` rows and surfaced as general + context-specific recommendations.
- Computes KPI scaffolding: total transactions, unique products, average basket size/reorder rate, top products, and contextual distributions for dashboards.

### 2.4 Auth, UX, and Delivery
- Email/OTP login with resend flow and console SMTP fallback; first-login store setup collects username/store name.
- Dashboard pages: upload wizard, threshold review, KPI cards, contextual market-basket sections, and download/report tiles.
- API blueprint exposes authenticated endpoints for recommendations, analytics payloads, and upload status for frontend charts.

---

## 3. Results Summary

| Area | Outcome |
| --- | --- |
| Data validation | Dual-schema normalization; null-handling across numeric/string columns |
| Thresholding | Percentile-based budget tiers; adaptive Apriori thresholds by volume; UI form → config pipeline |
| Context building | Budget, basket size, time-of-day/day-of-week, age group derivation for every order |
| Rule mining | General + context-aware association rules persisted for reuse and API delivery |
| Security/UX | OTP-gated sessions, first-time setup, profile updates, protected dashboards & APIs |
| Demo dataset insights | 500 orders, 15 products, ~2.4 items/order; spend p33≈337, p66≈433; top SKUs: Notebooks, Cheese, Chips, Folders, Bread |

---

## 4. Challenges Faced

### 4.1 Heterogeneous CSV Schemas
- **Issue:** Datasets varied between `order_id/product_id` and `transaction_id/product_name`.
- **Solution:** Normalization step in `_validate_data_structure` that hashes names into product IDs and aligns on `order_id`.
- **Impact:** Single analytics path regardless of source format.

### 4.2 Small-Sample Rule Quality
- **Issue:** Panel/demo files can be <20 transactions, leading to noisy rules.
- **Solution:** Adaptive thresholds that raise support/confidence for tiny samples and fallback simplified transactions when rows <5.
- **Trade-off:** Conservative rule volume in small demos, preserving precision over coverage.

### 4.3 OTP Deliverability
- **Issue:** SMTP variability during demos.
- **Solution:** Console-based email fallback (`EMAIL_ALLOW_CONSOLE=true`) plus resend endpoint; login pipeline stores session-bound OTP state.

---

## 5. Production Improvements

### 5.1 Short Term (1–2 weeks)
1. Cache rule generation outputs per upload to avoid recompute on every dashboard/API call.
2. Add client-side validations for CSV size/columns before upload to reduce failed jobs.
3. Wire lightweight smoke tests for OTP flow and upload/analytics API contract.

### 5.2 Medium Term (1–2 months)
1. Swap SQLite for Postgres in production; add migrations for analytics tables.
2. Introduce asynchronous processing queue (Celery/RQ) for large uploads and rule mining.
3. Add per-class threshold tuning via ROC/PR curves on historical data to refine recommendations.

### 5.3 Long Term (3–6 months)
1. Incremental learning of association rules to handle streaming receipts without full recompute.
2. Model-based recommenders (e.g., sequence models) to complement Apriori for cold-start products.
3. Monitoring/alerting: rule drift, upload errors, OTP delivery latency; add Grafana/Prometheus.

---

## 6. API & UX Notes

- **GET `/api/recommendations/<product_id>`** → Top co-buy targets with lift/confidence narratives (context-aware via query params `time_of_day`, `budget`, `basket_size`).
- **GET `/api/analytics/<upload_id>`** → JSON for charts (transactions, unique products, distributions, rule counts, top products/associations).
- **GET `/api/upload-status/<upload_id>`** → Upload metadata plus analytics readiness flag.
- **Dashboard highlights:** KPI cards (sales proxies, basket stats), busiest shopping moment, common budget range, leading shopper group, top associations with contextual callouts.

---

## 7. Conclusion

Delivered an end-to-end SmartCart experience: OTP-secured access, schema-tolerant uploads, guided thresholding, contextual market-basket mining, dashboards, and JSON endpoints ready for frontend/chart integrations. The sample dataset confirms the ingestion → analytics → recommendation loop works with realistic retail signals. Next focus areas are production hardening (DB, async jobs), test coverage, and monitoring.

---

## 8. Appendix

### Deliverables Checklist
- [x] Flask app factory with OTP auth, upload flow, dashboards
- [x] Threshold suggestion + recommendation pipeline
- [x] Retail analytics engine with contextual rule mining
- [x] Authenticated recommendation & analytics APIs
- [x] Sample datasets for demos
- [x] Technical report (this document) + README quickstart

### Repository Touchpoints
- Core app factory & config: `app/__init__.py`, `config.py`, `run.py`
- Auth & dashboards: `app/routes.py`, `app/forms.py`, templates under `app/templates`
- Analytics engine & thresholds: `app/analytics_engine.py`, `app/threshold_configurator.py`, `app/threshold_handler.py`
- Data models: `app/models.py`
- Demo data: `datasets/`

### Environment Snapshot
- macOS, Python 3.9+, Flask stack; sample run stats derived from `datasets/sample_multi_item_baskets.csv` (500 orders, 15 products).
