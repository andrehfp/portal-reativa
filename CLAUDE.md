# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Portal Reativa is a minimalist real estate property search portal with natural language processing capabilities in Portuguese. It connects to an existing SQLite database (`../reale-xml/conceito/data/properties.db`) containing property data imported from XML sources.

## Commands

### Development Server
```bash
# Run development server (auto-reload enabled)
python main.py
# Server runs on http://localhost:8000 with uvicorn auto-reload
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Git Workflow
```bash
# Feature branch naming convention
git checkout -b feature/[feature-name]

# Commonly used branches
# - main: production-ready code
# - feature/*: new features
```

## Architecture

### Backend Stack
- **FastAPI** application in `main.py` handling all routes and business logic
- **SQLite** database connection to `../reale-xml/conceito/data/properties.db`
- **Jinja2** server-side templating for HTML generation
- **HTMX** for dynamic updates without full page reloads

### Key Endpoints

1. **Home & Search** (`/` and `/search`)
   - Natural language search parsing in `parse_search_query()`
   - HTMX-powered real-time search with 500ms debounce
   - Returns `property_grid.html` component for dynamic updates

2. **Property Details** (`/imovel/{slug}`)
   - SEO-friendly URLs with slug generation
   - Legacy redirect from `/property/{id}` to new URL structure
   - HTML sanitization for property descriptions using bleach

### Search Implementation

The search system (`search_properties()` and `parse_search_query()`) understands:
- Price ranges: "até 500k", "acima de 200k"
- Property types: "casa", "apartamento", "terreno"
- Locations: "no centro", "em curitiba"  
- Bedrooms: "3 quartos", "2 dormitórios"
- Transaction types: "para venda", "para alugar"

### Frontend Structure

```
templates/
├── base.html                 # Base template with Tailwind CSS
├── index.html               # Homepage with search interface
├── property.html            # Property detail page with gallery
└── components/
    └── property_grid.html   # Reusable property cards grid
```

### Gallery System

- **gallery.js**: Full-featured image carousel with:
  - Thumbnail strip with scrolling
  - Wrap-around navigation
  - Zoom functionality
  - Keyboard shortcuts
  - Touch/swipe support
  
- **gallery.css**: Apple-inspired design with backdrop filters

### Database Schema

Properties table includes:
- Basic: id, title, type, transaction_type, status
- Pricing: price, condominium_fee, iptu_tax
- Details: bedrooms, suites, bathrooms, parking, area, total_area, useful_area
- Location: address, neighborhood, city, state, zipcode
- Content: description (HTML), images (JSON), features (JSON)
- Metadata: client_code, created_at, last_sync

## Development Notes

### HTMX Patterns
- Search uses `hx-get="/search"` with `hx-trigger="submit, keyup changed delay:500ms"`
- Target updates: `hx-target="#search-results"`
- Loading indicators: `hx-indicator="#search-spinner"`

### Property URL Generation
Properties use SEO-friendly slugs: `/imovel/{type}-{location}-{id}`
Example: `/imovel/casa-jardim-carvalho-123`

### JSON Field Handling
Images and features are stored as JSON strings in SQLite and parsed in Python:
```python
prop['images'] = json.loads(prop['images']) if prop['images'] else []
```

### Template Data Attributes
Gallery images passed via: `data-gallery-images='{{ property.images|tojson }}'`
Use single quotes to avoid JSON escaping issues.

## Current Branch Work

When on `feature/search-implementation`:
- Focus on fixing search functionality
- The search endpoint exists but may have query parsing issues
- Check SQL query construction in `parse_search_query()`
- Verify HTMX integration in templates