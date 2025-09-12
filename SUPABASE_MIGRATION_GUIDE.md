# Supabase Migration Guide

This guide explains how to migrate the Polaroo Utility Calculator from local storage to a fully Supabase-based system.

## 🎯 Migration Overview

The migration transforms the system from:
- **Before**: Mixed local files + partial Supabase storage
- **After**: Complete Supabase integration with proper database schema, file storage, and API

## 📋 What's Included

### 1. Database Schema (`supabase_schema.sql`)
- **Properties table**: All property information with room counts and allowances
- **Processing sessions**: Track each processing run
- **Property results**: Individual property processing results
- **Invoices**: Individual invoice records with file storage paths
- **File storage**: Metadata for all uploaded files
- **System settings**: Configuration and API keys
- **Indexes**: Optimized for performance
- **RLS policies**: Row-level security for data protection

### 2. New Supabase Client (`src/supabase_client.py`)
- **Data models**: Pydantic models for all database entities
- **SupabaseManager**: Complete CRUD operations for all tables
- **File storage**: Upload/download with proper path cleaning
- **Batch operations**: Efficient bulk data operations
- **Error handling**: Comprehensive error management

### 3. Updated Scraping (`src/polaroo_scrape_supabase.py`)
- **Full Supabase integration**: All data stored in database
- **Session management**: Track processing sessions
- **File storage**: Automatic PDF upload to Supabase Storage
- **Error handling**: Robust error management and recovery
- **Batch processing**: Process multiple properties efficiently

### 4. New API (`src/api_supabase.py`)
- **Complete REST API**: All operations via HTTP endpoints
- **Session management**: Track and retrieve processing sessions
- **Data export**: CSV/Excel export of results
- **Legacy compatibility**: Backward-compatible endpoints
- **Health checks**: Database and system status monitoring

### 5. Migration Tools
- **Setup script** (`setup_supabase.py`): Initialize database
- **Test suite** (`test_supabase_migration.py`): Verify migration
- **Legacy compatibility** (`src/load_supabase.py`): Maintain existing code

## 🚀 Migration Steps

### Step 1: Set Up Supabase Database

1. **Run the setup script**:
   ```bash
   python setup_supabase.py
   ```

2. **Verify database creation**:
   - Check Supabase dashboard for new tables
   - Verify data was inserted correctly
   - Test database functions

### Step 2: Test the Migration

1. **Run the test suite**:
   ```bash
   python test_supabase_migration.py
   ```

2. **Verify all tests pass**:
   - Database connection
   - Property operations
   - File storage
   - API compatibility

### Step 3: Update Your Application

1. **Replace API imports**:
   ```python
   # Old
   from src.api import app
   
   # New
   from src.api_supabase import app
   ```

2. **Update scraping imports**:
   ```python
   # Old
   from src.polaroo_scrape import process_property_invoices
   
   # New
   from src.polaroo_scrape_supabase import process_property_invoices
   ```

### Step 4: Test the New System

1. **Start the new API**:
   ```bash
   python -m src.api_supabase
   ```

2. **Test endpoints**:
   ```bash
   # Health check
   curl http://localhost:8000/api/health
   
   # Get properties
   curl http://localhost:8000/api/properties
   
   # Process a property
   curl -X POST http://localhost:8000/api/process-property \
     -H "Content-Type: application/json" \
     -d '{"property_name": "Aribau 1º 1ª"}'
   ```

## 🔧 Configuration

### Environment Variables

Ensure your `.env2` file contains:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
STORAGE_BUCKET=polaroo_pdfs
POLAROO_EMAIL=your_email
POLAROO_PASSWORD=your_password
COHERE_API_KEY=your_cohere_key
```

### Supabase Storage

1. **Create storage bucket**: `polaroo_pdfs`
2. **Set up policies**: Allow service role full access
3. **Configure CORS**: For web access if needed

## 📊 New API Endpoints

### Property Management
- `GET /api/properties` - Get all properties
- `GET /api/properties/{name}/allowance` - Get property allowance

### Processing
- `POST /api/process-property` - Process single property
- `POST /api/process-batch` - Process multiple properties
- `POST /api/process-first-10` - Process first 10 properties

### Session Management
- `GET /api/sessions` - Get all processing sessions
- `GET /api/sessions/{id}` - Get specific session
- `GET /api/sessions/{id}/results` - Get session results

### Data Export
- `GET /api/export/session/{id}/csv` - Export session as CSV
- `GET /api/export/session/{id}/excel` - Export session as Excel

### Configuration
- `GET /api/configuration` - Get system configuration
- `GET /api/system-settings` - Get system settings

### Legacy Compatibility
- `POST /api/calculate` - Legacy calculation endpoint
- `GET /api/health` - Health check

## 🗄️ Database Schema

### Core Tables

1. **properties**: Property information and room counts
2. **room_limits**: Allowance limits by room count
3. **processing_sessions**: Processing run metadata
4. **property_results**: Individual property results
5. **invoices**: Invoice records with file paths
6. **file_storage**: File metadata and storage paths
7. **monthly_service_data**: Historical monthly data
8. **system_settings**: Configuration values
9. **api_credentials**: API keys and credentials

### Key Features

- **UUIDs**: All primary keys use UUIDs
- **Timestamps**: Created/updated timestamps on all tables
- **Indexes**: Optimized for common queries
- **RLS**: Row-level security enabled
- **Functions**: Database functions for common operations
- **Triggers**: Automatic timestamp updates

## 🔄 Data Migration

### Existing Data

The migration includes:
- **Properties**: All 100+ properties with room counts
- **Room limits**: Standard allowance structure
- **System settings**: Default configuration values

### File Storage

- **Path cleaning**: Special characters handled properly
- **Organized structure**: Files organized by property
- **Metadata tracking**: Full file information stored

## 🚨 Important Notes

### Breaking Changes

1. **API endpoints**: Some endpoints have changed
2. **Data format**: Response formats may differ
3. **File paths**: Storage paths are now cleaned
4. **Error handling**: More detailed error responses

### Backward Compatibility

- **Legacy functions**: Old functions still work
- **API compatibility**: Legacy endpoints maintained
- **Data format**: Compatible response formats

### Performance

- **Database indexes**: Optimized for common queries
- **Batch operations**: Efficient bulk operations
- **Connection pooling**: Reused database connections
- **File storage**: CDN-backed file delivery

## 🐛 Troubleshooting

### Common Issues

1. **Database connection failed**:
   - Check Supabase URL and service key
   - Verify network connectivity
   - Check Supabase project status

2. **File upload failed**:
   - Check storage bucket exists
   - Verify storage policies
   - Check file path cleaning

3. **Property not found**:
   - Verify property name spelling
   - Check database has properties loaded
   - Run setup script again

4. **API errors**:
   - Check environment variables
   - Verify database schema
   - Check logs for detailed errors

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Checks

Use the health check endpoints:
- `GET /api/health` - Basic health check
- `GET /api/health/detailed` - Detailed system status

## 📈 Monitoring

### Database Monitoring

- **Supabase Dashboard**: Monitor queries and performance
- **Logs**: Check application logs for errors
- **Metrics**: Track processing success rates

### File Storage Monitoring

- **Storage usage**: Monitor bucket size
- **Upload success**: Track file upload success rates
- **Download metrics**: Monitor file access patterns

## 🔒 Security

### Row Level Security (RLS)

- **Enabled**: All tables have RLS enabled
- **Service role**: Full access for API operations
- **User access**: Can be configured for user-specific access

### API Security

- **CORS**: Configured for web access
- **Authentication**: Can be added for user authentication
- **Rate limiting**: Can be implemented for API protection

## 🚀 Deployment

### Production Deployment

1. **Set up Supabase project**:
   - Create production Supabase project
   - Configure storage bucket
   - Set up RLS policies

2. **Deploy application**:
   - Update environment variables
   - Deploy to your platform
   - Test all endpoints

3. **Monitor system**:
   - Set up monitoring
   - Configure alerts
   - Regular health checks

### Environment Configuration

- **Development**: Use test Supabase project
- **Staging**: Use staging Supabase project
- **Production**: Use production Supabase project

## 📚 Additional Resources

- **Supabase Documentation**: https://supabase.com/docs
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Playwright Documentation**: https://playwright.dev/

## 🤝 Support

If you encounter issues during migration:

1. **Check logs**: Review application and database logs
2. **Run tests**: Use the test suite to identify issues
3. **Verify setup**: Ensure database schema is correct
4. **Check configuration**: Verify all environment variables

The migration provides a robust, scalable foundation for the Polaroo Utility Calculator with full cloud integration and modern database architecture.
