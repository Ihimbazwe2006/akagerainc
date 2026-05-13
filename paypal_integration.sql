-- PayPal Payment System Database Migration
-- Run this script to add PayPal support to your database
-- Date: May 12, 2026

-- ============================================================================
-- Step 1: Add PayPal columns to payments table
-- ============================================================================

ALTER TABLE payments
ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) DEFAULT 'paypal',
ADD COLUMN IF NOT EXISTS paypal_order_id VARCHAR(255) UNIQUE;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_paypal_order_id ON payments(paypal_order_id);
CREATE INDEX IF NOT EXISTS idx_payment_method ON payments(payment_method);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- ============================================================================
-- Step 2: Add constraints to ensure data integrity
-- ============================================================================

-- Add constraint to ensure payment_method is valid
ALTER TABLE payments 
ADD CONSTRAINT check_payment_method 
CHECK (payment_method IN ('paypal', 'card', 'momo', 'bank_transfer'));

-- ============================================================================
-- Step 3: Create PayPal transactions log (optional, for audit trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS paypal_transactions (
    id SERIAL PRIMARY KEY,
    payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    paypal_order_id VARCHAR(255) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL, -- 'create', 'capture', 'refund'
    paypal_response JSONB, -- Store full PayPal API response
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_paypal_transactions_order_id ON paypal_transactions(paypal_order_id);
CREATE INDEX IF NOT EXISTS idx_paypal_transactions_payment_id ON paypal_transactions(payment_id);

-- ============================================================================
-- Step 4: Add PayPal configuration table (for storing API keys encrypted)
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    is_encrypted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default PayPal configuration keys (values should be set via ENV)
INSERT INTO payment_config (key, value, is_encrypted) VALUES
    ('paypal_environment', 'sandbox', FALSE),
    ('paypal_enabled', 'true', FALSE),
    ('card_enabled', 'false', FALSE),
    ('momo_enabled', 'false', FALSE)
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Step 5: Add payment processing queue (for async processing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS payment_queue (
    id SERIAL PRIMARY KEY,
    payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- 'create_order', 'capture_order', 'refund'
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_payment_queue_status ON payment_queue(status);
CREATE INDEX IF NOT EXISTS idx_payment_queue_payment_id ON payment_queue(payment_id);

-- ============================================================================
-- Step 6: Create statistics views
-- ============================================================================

-- Payment statistics view
CREATE OR REPLACE VIEW v_payment_stats AS
SELECT 
    payment_method,
    status,
    COUNT(*) as total_transactions,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    MIN(created_at) as first_transaction,
    MAX(created_at) as last_transaction
FROM payments
GROUP BY payment_method, status;

-- PayPal specific statistics
CREATE OR REPLACE VIEW v_paypal_stats AS
SELECT 
    status,
    COUNT(*) as total_orders,
    SUM(amount) as total_revenue,
    AVG(amount) as average_order_value,
    MIN(created_at) as oldest_order,
    MAX(created_at) as latest_order
FROM payments
WHERE payment_method = 'paypal'
GROUP BY status;

-- ============================================================================
-- Step 7: Create audit logging function
-- ============================================================================

CREATE OR REPLACE FUNCTION log_payment_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IS DISTINCT FROM OLD.status THEN
        INSERT INTO paypal_transactions 
        (payment_id, paypal_order_id, transaction_type, status)
        VALUES 
        (NEW.id, NEW.paypal_order_id, 'status_change', NEW.status);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if it exists
DROP TRIGGER IF EXISTS trigger_payment_audit ON payments;

-- Create trigger
CREATE TRIGGER trigger_payment_audit
AFTER UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION log_payment_change();

-- ============================================================================
-- Step 8: Add useful helper functions
-- ============================================================================

-- Function to get pending PayPal payments
CREATE OR REPLACE FUNCTION get_pending_paypal_payments()
RETURNS TABLE (
    id INTEGER,
    user_id INTEGER,
    amount NUMERIC,
    paypal_order_id VARCHAR,
    created_at TIMESTAMP
) AS $$
SELECT 
    id,
    user_id,
    amount,
    paypal_order_id,
    created_at
FROM payments
WHERE payment_method = 'paypal' 
    AND status = 'pending'
    AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
$$ LANGUAGE SQL;

-- Function to get payment statistics for a user
CREATE OR REPLACE FUNCTION get_user_payment_stats(p_user_id INTEGER)
RETURNS TABLE (
    total_payments BIGINT,
    completed_payments BIGINT,
    failed_payments BIGINT,
    total_spent NUMERIC,
    average_payment NUMERIC
) AS $$
SELECT 
    COUNT(*) as total_payments,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_payments,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
    COALESCE(SUM(amount), 0) as total_spent,
    COALESCE(AVG(amount), 0) as average_payment
FROM payments
WHERE user_id = p_user_id;
$$ LANGUAGE SQL;

-- ============================================================================
-- Step 9: Grant permissions (adjust based on your user setup)
-- ============================================================================

-- Grant select on all new tables to read-only role (if you have one)
-- GRANT SELECT ON v_payment_stats, v_paypal_stats TO read_only_user;

-- ============================================================================
-- Verification Queries (Run these to verify installation)
-- ============================================================================

-- Check that columns were added
-- SELECT column_name, data_type FROM information_schema.columns 
-- WHERE table_name = 'payments' AND column_name IN ('payment_method', 'paypal_order_id');

-- Check that indexes were created
-- SELECT indexname FROM pg_indexes WHERE tablename = 'payments';

-- Check payment statistics
-- SELECT * FROM v_payment_stats;

-- ============================================================================
-- Rollback Script (if needed)
-- ============================================================================

/*
-- To rollback these changes, run:

DROP TRIGGER IF EXISTS trigger_payment_audit ON payments;
DROP FUNCTION IF EXISTS log_payment_change();
DROP FUNCTION IF EXISTS get_pending_paypal_payments();
DROP FUNCTION IF EXISTS get_user_payment_stats(INTEGER);
DROP VIEW IF EXISTS v_payment_stats;
DROP VIEW IF EXISTS v_paypal_stats;
DROP TABLE IF EXISTS payment_queue;
DROP TABLE IF EXISTS payment_config;
DROP TABLE IF EXISTS paypal_transactions;

ALTER TABLE payments 
DROP CONSTRAINT IF EXISTS check_payment_method;

ALTER TABLE payments 
DROP COLUMN IF EXISTS paypal_order_id;
ALTER TABLE payments 
DROP COLUMN IF EXISTS payment_method;

DROP INDEX IF EXISTS idx_paypal_order_id;
DROP INDEX IF EXISTS idx_payment_method;
DROP INDEX IF EXISTS idx_payments_status;
DROP INDEX IF EXISTS idx_paypal_transactions_order_id;
DROP INDEX IF EXISTS idx_paypal_transactions_payment_id;
DROP INDEX IF EXISTS idx_payment_queue_status;
DROP INDEX IF EXISTS idx_payment_queue_payment_id;
*/

-- ============================================================================
-- End of Migration Script
-- ============================================================================
