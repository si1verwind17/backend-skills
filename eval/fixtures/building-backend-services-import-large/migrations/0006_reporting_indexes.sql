-- Supports the operator reports: occupancy scans reservations by garage
-- and window, revenue scans charges by garage and settlement time.

CREATE INDEX ix_reservation_garage_status_window
    ON reservation (garage_id, status, window_start, window_end);

CREATE INDEX ix_reservation_completed_unsettled
    ON reservation (completed_at)
    WHERE status = 'completed';
