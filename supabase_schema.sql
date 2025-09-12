-- Supabase Database Schema for Polaroo Utility Calculator
-- This schema migrates all functionality to Supabase

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================
-- CORE CONFIGURATION TABLES
-- =============================================

-- Properties/Addresses table
CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    room_count INTEGER NOT NULL DEFAULT 1,
    special_allowance DECIMAL(10,2),
    building_key TEXT NOT NULL,
    floor_code TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Room-based allowance limits
CREATE TABLE IF NOT EXISTS room_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    room_count INTEGER NOT NULL UNIQUE,
    allowance DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- INVOICE PROCESSING TABLES
-- =============================================

-- Processing sessions (each time we run the full process)
CREATE TABLE IF NOT EXISTS processing_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_name TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    total_properties INTEGER DEFAULT 0,
    successful_properties INTEGER DEFAULT 0,
    failed_properties INTEGER DEFAULT 0,
    total_cost DECIMAL(12,2) DEFAULT 0,
    total_overuse DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Property processing results
CREATE TABLE IF NOT EXISTS property_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES processing_sessions(id) ON DELETE CASCADE,
    property_id UUID REFERENCES properties(id),
    property_name TEXT NOT NULL,
    room_count INTEGER NOT NULL,
    allowance DECIMAL(10,2) NOT NULL,
    total_electricity_cost DECIMAL(10,2) DEFAULT 0,
    total_water_cost DECIMAL(10,2) DEFAULT 0,
    total_cost DECIMAL(10,2) DEFAULT 0,
    overuse DECIMAL(10,2) DEFAULT 0,
    selected_invoices_count INTEGER DEFAULT 0,
    downloaded_files_count INTEGER DEFAULT 0,
    llm_reasoning TEXT,
    processing_status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Individual invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_result_id UUID REFERENCES property_results(id) ON DELETE CASCADE,
    invoice_number TEXT NOT NULL,
    service_type TEXT NOT NULL, -- electricity, water, gas
    amount DECIMAL(10,2) NOT NULL,
    invoice_date DATE,
    period_start DATE,
    period_end DATE,
    provider TEXT,
    contract_code TEXT,
    is_selected BOOLEAN DEFAULT false,
    is_downloaded BOOLEAN DEFAULT false,
    file_path TEXT, -- Supabase Storage path
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- FILE STORAGE TABLES
-- =============================================

-- File storage metadata
CREATE TABLE IF NOT EXISTS file_storage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_name TEXT NOT NULL,
    invoice_number TEXT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL, -- Supabase Storage path
    file_size INTEGER NOT NULL,
    content_type TEXT NOT NULL,
    storage_bucket TEXT NOT NULL,
    md5_hash TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- HISTORICAL DATA TABLES
-- =============================================

-- Monthly service data (from Excel processing)
CREATE TABLE IF NOT EXISTS monthly_service_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    property_name TEXT NOT NULL,
    report_date DATE NOT NULL,
    electricity_cost DECIMAL(10,2) DEFAULT 0,
    water_cost DECIMAL(10,2) DEFAULT 0,
    total_cost DECIMAL(10,2) DEFAULT 0,
    allowance DECIMAL(10,2) DEFAULT 0,
    total_extra DECIMAL(10,2) DEFAULT 0,
    electricity_extra DECIMAL(10,2) DEFAULT 0,
    water_extra DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Raw report files
CREATE TABLE IF NOT EXISTS raw_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_date DATE NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL, -- Supabase Storage path
    file_size INTEGER NOT NULL,
    md5_hash TEXT NOT NULL,
    processing_status TEXT DEFAULT 'pending', -- pending, processed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- SYSTEM CONFIGURATION TABLES
-- =============================================

-- System settings
CREATE TABLE IF NOT EXISTS system_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- API keys and credentials
CREATE TABLE IF NOT EXISTS api_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service_name TEXT NOT NULL UNIQUE,
    api_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================
-- INDEXES FOR PERFORMANCE
-- =============================================

-- Properties indexes
CREATE INDEX IF NOT EXISTS idx_properties_name ON properties(name);
CREATE INDEX IF NOT EXISTS idx_properties_building_key ON properties(building_key);

-- Processing sessions indexes
CREATE INDEX IF NOT EXISTS idx_processing_sessions_dates ON processing_sessions(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_processing_sessions_status ON processing_sessions(status);

-- Property results indexes
CREATE INDEX IF NOT EXISTS idx_property_results_session ON property_results(session_id);
CREATE INDEX IF NOT EXISTS idx_property_results_property ON property_results(property_id);
CREATE INDEX IF NOT EXISTS idx_property_results_name ON property_results(property_name);

-- Invoices indexes
CREATE INDEX IF NOT EXISTS idx_invoices_property_result ON invoices(property_result_id);
CREATE INDEX IF NOT EXISTS idx_invoices_service_type ON invoices(service_type);
CREATE INDEX IF NOT EXISTS idx_invoices_selected ON invoices(is_selected);

-- File storage indexes
CREATE INDEX IF NOT EXISTS idx_file_storage_property ON file_storage(property_name);
CREATE INDEX IF NOT EXISTS idx_file_storage_bucket ON file_storage(storage_bucket);

-- Monthly data indexes
CREATE INDEX IF NOT EXISTS idx_monthly_data_property_date ON monthly_service_data(property_name, report_date);

-- =============================================
-- ROW LEVEL SECURITY (RLS)
-- =============================================

-- Enable RLS on all tables
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE room_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE file_storage ENABLE ROW LEVEL SECURITY;
ALTER TABLE monthly_service_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_credentials ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access (for API)
CREATE POLICY "Service role can do everything" ON properties FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON room_limits FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON processing_sessions FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON property_results FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON invoices FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON file_storage FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON monthly_service_data FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON raw_reports FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON system_settings FOR ALL USING (true);
CREATE POLICY "Service role can do everything" ON api_credentials FOR ALL USING (true);

-- =============================================
-- INITIAL DATA POPULATION
-- =============================================

-- Insert room limits
INSERT INTO room_limits (room_count, allowance) VALUES
(1, 50.00),
(2, 70.00),
(3, 100.00),
(4, 130.00)
ON CONFLICT (room_count) DO UPDATE SET allowance = EXCLUDED.allowance;

-- Insert properties from the current system
INSERT INTO properties (name, room_count, special_allowance, building_key, floor_code) VALUES
-- Aribau properties
('Aribau 1º 1ª', 1, NULL, 'ARIBAU', '1-1'),
('Aribau 1º 2ª', 1, NULL, 'ARIBAU', '1-2'),
('Aribau 2º 1º', 1, NULL, 'ARIBAU', '2-1'),
('Aribau 2º 2º', 3, NULL, 'ARIBAU', '2-2'),
('Aribau 2º 3ª', 1, NULL, 'ARIBAU', '2-3'),
('Aribau 126-128 3-1', 3, NULL, 'ARIBAU', '3-1'),
('Aribau 3º 2ª', 3, NULL, 'ARIBAU', '3-2'),
('Aribau 4º 1ª', 3, NULL, 'ARIBAU', '4-1'),
('Aribau 4º 1ª B', 2, NULL, 'ARIBAU', '4-1B'),
('Aribau 4º 2ª', 3, NULL, 'ARIBAU', '4-2'),
('Aribau Escalera', 1, NULL, 'ARIBAU', 'ESCALERA'),

-- Bisbe Laguarda properties
('Bisbe Laguarda 14, Pral-2', 3, NULL, 'BISBELAGUARDA', 'PRAL-2'),
('Bisbe Laguarda 14, 2-2', 3, NULL, 'BISBELAGUARDA', '2-2'),

-- Blasco de Garay properties
('Blasco de Garay Pral 1ª', 3, NULL, 'BLASCOGARAY', 'PRAL-1'),
('Blasco de Garay Pral 2ª', 3, NULL, 'BLASCOGARAY', 'PRAL-2'),
('Blasco de Garay 1º 1ª', 3, NULL, 'BLASCOGARAY', '1-1'),
('Blasco de Garay 1º-2', 2, NULL, 'BLASCOGARAY', '1-2'),
('Blasco de Garay 2º 1ª', 3, NULL, 'BLASCOGARAY', '2-1'),
('Blasco de Garay 2º 2ª', 3, NULL, 'BLASCOGARAY', '2-2'),
('Blasco de Garay 3º 1ª', 3, NULL, 'BLASCOGARAY', '3-1'),
('Blasco de Garay 3º 2ª', 3, NULL, 'BLASCOGARAY', '3-2'),
('Blasco de Garay 4º 1ª', 3, NULL, 'BLASCOGARAY', '4-1'),
('Blasco de Garay 5º 1ª', 1, NULL, 'BLASCOGARAY', '5-1'),

-- Comte Borrell properties
('Comte Borrell Pral 1ª', 3, NULL, 'COMTEBORRELL', 'PRAL-1'),
('Comte Borrell 5º 1ª', 1, NULL, 'COMTEBORRELL', '5-1'),
('Comte Borrell 5º 2ª', 1, NULL, 'COMTEBORRELL', '5-2'),

-- Llull 250 properties
('Llull 250 Pral 3', 2, NULL, 'LLULL250', 'PRAL-3'),
('Llull 250 Pral 5', 2, NULL, 'LLULL250', 'PRAL-5'),
('Llull 250 1-1', 2, NULL, 'LLULL250', '1-1'),
('Llull 250 1-3', 2, NULL, 'LLULL250', '1-3'),
('Llull 250 1-4', 2, NULL, 'LLULL250', '1-4'),
('Llull 250 1-5', 2, NULL, 'LLULL250', '1-5'),
('Llull 250 1-6', 2, NULL, 'LLULL250', '1-6'),
('Llull 250 2-3', 2, NULL, 'LLULL250', '2-3'),
('Llull 250 2-5', 2, NULL, 'LLULL250', '2-5'),
('Llull 250 2-6', 2, NULL, 'LLULL250', '2-6'),
('Llull 250 3-2', 2, NULL, 'LLULL250', '3-2'),
('Llull 250 3-4', 2, NULL, 'LLULL250', '3-4'),
('Llull 250 3-5', 2, NULL, 'LLULL250', '3-5'),
('Llull 250 3-6', 2, NULL, 'LLULL250', '3-6'),
('Llull 250 4-3', 2, NULL, 'LLULL250', '4-3'),
('Llull 250 4-5', 2, NULL, 'LLULL250', '4-5'),
('Llull 250 5-1', 2, NULL, 'LLULL250', '5-1'),
('Llull 250 5-2', 2, NULL, 'LLULL250', '5-2'),
('Llull 250 5-3', 2, NULL, 'LLULL250', '5-3'),
('Llull 250 5-4', 2, NULL, 'LLULL250', '5-4'),
('Llull 250 5-5', 2, NULL, 'LLULL250', '5-5'),

-- Padilla properties
('Padilla Entl 1ª', 1, NULL, 'PADILLA', 'ENTL-1'),
('Padilla Entl 2ª', 1, NULL, 'PADILLA', 'ENTL-2'),
('Padilla Entl 4ª', 1, NULL, 'PADILLA', 'ENTL-4'),
('Padilla Pral 2ª', 1, NULL, 'PADILLA', 'PRAL-2'),
('Padilla Pral 3ª', 1, NULL, 'PADILLA', 'PRAL-3'),
('Padilla 1º 1ª', 3, NULL, 'PADILLA', '1-1'),
('Padilla 1º 2ª', 3, NULL, 'PADILLA', '1-2'),
('Padilla 1º 3ª', 3, 150.00, 'PADILLA', '1-3'), -- Special allowance
('Padilla 2º 1ª', 1, NULL, 'PADILLA', '2-1'),
('Padilla 2-2', 1, NULL, 'PADILLA', '2-2'),
('Padilla 2º 3ª', 1, NULL, 'PADILLA', '2-3'),
('Padilla 2-4', 1, NULL, 'PADILLA', '2-4'),
('Padilla 3º 2ª', 1, NULL, 'PADILLA', '3-2'),
('Padilla 3º 3ª', 1, NULL, 'PADILLA', '3-3'),
('Padilla 4º 2ª', 1, NULL, 'PADILLA', '4-2'),
('Padilla 4º 3ª', 1, NULL, 'PADILLA', '4-3'),
('Padilla 5º 1ª', 1, NULL, 'PADILLA', '5-1'),
('Padilla 5º 2ª', 1, NULL, 'PADILLA', '5-2'),

-- Psg Sant Joan properties
('Psg Sant Joan Entl 1ª', 1, NULL, 'PSGSANTJOAN', 'ENTL-1'),
('Psg Sant Joan Entl 2ª', 1, NULL, 'PSGSANTJOAN', 'ENTL-2'),
('Psg Sant Joan Pral 1ª', 1, NULL, 'PSGSANTJOAN', 'PRAL-1'),
('Psg Sant Joan Pral 2ª', 1, NULL, 'PSGSANTJOAN', 'PRAL-2'),
('Psg Sant Joan 1º 1ª', 1, NULL, 'PSGSANTJOAN', '1-1'),
('Pg Sant Joan 161 2-1', 1, NULL, 'PSGSANTJOAN', '2-1'),
('Pg Sant Joan 161 2-2', 1, NULL, 'PSGSANTJOAN', '2-2'),
('Psg Sant Joan 3º 2ª', 1, NULL, 'PSGSANTJOAN', '3-2'),
('Pg Sant Joan 4-1', 1, NULL, 'PSGSANTJOAN', '4-1'),
('Psg Sant Joan 4º 2ª', 1, NULL, 'PSGSANTJOAN', '4-2'),
('Psg Sant Joan 5º 2ª', 1, NULL, 'PSGSANTJOAN', '5-2'),

-- Providencia properties
('Providencia Bajs 2ª', 2, NULL, 'PROVIDENCIA', 'BAJO-2'),
('Providencia Pral 2ª', 2, NULL, 'PROVIDENCIA', 'PRAL-2'),
('Providencia 1º 1ª', 1, NULL, 'PROVIDENCIA', '1-1'),
('Providencia 1º 2ª', 1, NULL, 'PROVIDENCIA', '1-2'),
('Providencia 2º 1ª', 1, NULL, 'PROVIDENCIA', '2-1'),
('Providencia 2º 2ª', 1, NULL, 'PROVIDENCIA', '2-2'),
('Providencia 3º 2ª', 1, NULL, 'PROVIDENCIA', '3-2'),
('Providencia 4º 2ª', 1, NULL, 'PROVIDENCIA', '4-2'),

-- Sardenya properties
('Sardenya 1º 2ª', 2, NULL, 'SARDENYA', '1-2'),
('Sardenya 3º 2ª', 2, NULL, 'SARDENYA', '3-2'),
('Sardenya 4º 2ª', 2, NULL, 'SARDENYA', '4-2'),
('Sardenya 5º 2ª', 2, NULL, 'SARDENYA', '5-2'),
('Sardenya Pral', 1, NULL, 'SARDENYA', 'PRAL'),

-- Torrent Olla properties
('Torrent Olla Pral 1ª', 1, NULL, 'TORRENTOLLA', 'PRAL-1'),
('Torrent Olla 1º 1ª', 1, NULL, 'TORRENTOLLA', '1-1'),
('Torrent Olla 1º 2ª', 1, NULL, 'TORRENTOLLA', '1-2'),
('Torrent Olla 2º 1ª', 1, NULL, 'TORRENTOLLA', '2-1'),
('Torrent Olla 2º 2ª', 1, NULL, 'TORRENTOLLA', '2-2'),
('Torrent Olla 3º 2ª', 1, NULL, 'TORRENTOLLA', '3-2'),
('Torrent Olla Ático', 1, NULL, 'TORRENTOLLA', 'ATICO'),

-- Valencia properties
('Valencia Pral 1ª', 1, NULL, 'VALENCIA', 'PRAL-1'),
('Valencia 2º 1ª', 1, NULL, 'VALENCIA', '2-1')
ON CONFLICT (name) DO UPDATE SET 
    room_count = EXCLUDED.room_count,
    special_allowance = EXCLUDED.special_allowance,
    building_key = EXCLUDED.building_key,
    floor_code = EXCLUDED.floor_code;

-- Insert system settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('cohere_api_key', '9MdzGhunt8Nrc9cwFdBl3GvlRWRIkGLN4VPma3Yp', 'Cohere API key for LLM processing'),
('storage_bucket', 'polaroo_pdfs', 'Supabase Storage bucket name'),
('storage_prefix', 'raw', 'Storage path prefix'),
('default_room_allowance', '50', 'Default allowance for 1-room properties'),
('max_concurrent_downloads', '5', 'Maximum concurrent PDF downloads'),
('browser_timeout', '30000', 'Browser timeout in milliseconds')
ON CONFLICT (setting_key) DO UPDATE SET setting_value = EXCLUDED.setting_value;

-- =============================================
-- FUNCTIONS AND TRIGGERS
-- =============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_properties_updated_at BEFORE UPDATE ON properties FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_property_results_updated_at BEFORE UPDATE ON property_results FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_system_settings_updated_at BEFORE UPDATE ON system_settings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_api_credentials_updated_at BEFORE UPDATE ON api_credentials FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get allowance for a property
CREATE OR REPLACE FUNCTION get_property_allowance(property_name TEXT)
RETURNS DECIMAL(10,2) AS $$
DECLARE
    allowance DECIMAL(10,2);
BEGIN
    SELECT COALESCE(p.special_allowance, rl.allowance)
    INTO allowance
    FROM properties p
    LEFT JOIN room_limits rl ON p.room_count = rl.room_count
    WHERE p.name = property_name;
    
    RETURN COALESCE(allowance, 50.00);
END;
$$ LANGUAGE plpgsql;

-- Function to clean file paths for storage
CREATE OR REPLACE FUNCTION clean_file_path(input_path TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Replace special characters that cause issues in Supabase Storage
    RETURN regexp_replace(
        regexp_replace(
            regexp_replace(input_path, '[ºª]', '', 'g'),
            '[^a-zA-Z0-9._/-]', '_', 'g'
        ),
        '_+', '_', 'g'
    );
END;
$$ LANGUAGE plpgsql;
