from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from slugify import slugify
import bleach
from markupsafe import Markup

app = FastAPI(title="Portal Reativa", description="Portal de propriedades imobiliárias")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_PATH = "../reale-xml/conceito/data/properties.db"

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, q: Optional[str] = None, page: int = 1):
    properties = []
    total = 0
    per_page = 12
    
    if q:
        properties, total = search_properties(q, page, per_page)
    else:
        # Show recent properties when no search query
        properties, total = get_recent_properties(page, per_page)
    
    total_pages = (total + per_page - 1) // per_page
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "properties": properties,
        "query": q or "",
        "current_page": page,
        "total_pages": total_pages,
        "total": total
    })

@app.get("/search")
async def search_api(request: Request, q: str = Query(...), page: int = 1):
    properties, total = search_properties(q, page, 12)
    total_pages = (total + 12 - 1) // 12
    
    return templates.TemplateResponse("components/property_grid.html", {
        "request": request,
        "properties": properties,
        "query": q,
        "current_page": page,
        "total_pages": total_pages,
        "total": total
    })

@app.get("/imovel/{slug}", response_class=HTMLResponse)
async def property_detail_by_slug(request: Request, slug: str):
    """New SEO-friendly property detail route"""
    # Extract property ID from slug (last part after final dash)
    try:
        property_id = int(slug.split('-')[-1])
    except (ValueError, IndexError):
        # Invalid slug format, redirect to home
        return RedirectResponse(url="/", status_code=301)
    
    property_data = get_property_by_id(property_id)
    if not property_data:
        return RedirectResponse(url="/", status_code=301)
    
    # Check if the current slug matches the canonical slug
    canonical_slug = property_data['slug']
    if slug != canonical_slug:
        # Redirect to canonical URL for SEO
        return RedirectResponse(url=f"/imovel/{canonical_slug}", status_code=301)
    
    return templates.TemplateResponse("property.html", {
        "request": request,
        "property": property_data
    })

@app.get("/property/{property_id}", response_class=HTMLResponse)
async def property_detail_redirect(request: Request, property_id: int):
    """Legacy route - redirect to SEO-friendly URL"""
    property_data = get_property_by_id(property_id)
    if not property_data:
        return RedirectResponse(url="/", status_code=301)
    
    # Redirect to new SEO-friendly URL
    return RedirectResponse(url=f"/imovel/{property_data['slug']}", status_code=301)

def get_recent_properties(page: int = 1, per_page: int = 12) -> tuple[List[Dict[str, Any]], int]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Count total active properties
    count_query = "SELECT COUNT(*) as total FROM properties WHERE status = 'active'"
    cursor = conn.execute(count_query)
    total = cursor.fetchone()['total']
    
    # Get recent properties ordered by created_at
    query = """
        SELECT * FROM properties 
        WHERE status = 'active' 
        ORDER BY created_at DESC 
        LIMIT ? OFFSET ?
    """
    offset = (page - 1) * per_page
    cursor = conn.execute(query, [per_page, offset])
    
    properties = []
    for row in cursor.fetchall():
        prop = dict(row)
        # Parse JSON fields
        if prop['images']:
            try:
                prop['images'] = json.loads(prop['images'])
            except:
                prop['images'] = []
        if prop['features']:
            try:
                prop['features'] = json.loads(prop['features'])
            except:
                prop['features'] = []
        
        # Format price
        if prop['price']:
            prop['formatted_price'] = format_price(prop['price'])
        
        # Generate slug for SEO-friendly URLs
        prop['slug'] = generate_property_slug(prop)
        
        properties.append(prop)
    
    conn.close()
    return properties, total

def get_property_by_id(property_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cursor = conn.execute(
        "SELECT * FROM properties WHERE id = ? AND status = 'active'",
        [property_id]
    )
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    property_data = dict(row)
    
    # Parse JSON fields
    if property_data['images']:
        try:
            property_data['images'] = json.loads(property_data['images'])
        except:
            property_data['images'] = []
    if property_data['features']:
        try:
            property_data['features'] = json.loads(property_data['features'])
        except:
            property_data['features'] = []
    
    # Format price
    if property_data['price']:
        property_data['formatted_price'] = format_price(property_data['price'])
    
    # Calculate price per square meter
    if property_data['price'] and property_data.get('area'):
        property_data['price_per_sqm'] = calculate_price_per_sqm(property_data['price'], property_data['area'])
    
    # Generate SEO-friendly slug
    property_data['slug'] = generate_property_slug(property_data)
    
    # Sanitize HTML description
    if property_data.get('description'):
        property_data['description_html'] = sanitize_html_description(property_data['description'])
    
    conn.close()
    return property_data

# Property abbreviation dictionary for common Brazilian real estate terms
PROPERTY_ABBREVIATIONS = {
    # Location prefixes
    'jd': 'jardim',
    'jrd': 'jardim',
    'vl': 'vila',
    'pq': 'parque',
    'st': 'santo',
    'sta': 'santa',
    'res': 'residencial',
    'cond': 'condomínio',
    'cjto': 'conjunto',
    
    # Property types
    'ap': 'apartamento',
    'apto': 'apartamento',
    'aptos': 'apartamentos',
    'ed': 'edifício',
    'cj': 'conjunto',
    'sl': 'sala',
    
    # Streets and addresses
    'av': 'avenida',
    'r': 'rua',
    'trav': 'travessa',
    'al': 'alameda',
    'pca': 'praça',
    'est': 'estrada',
    
    # Common city abbreviations (Brazil)
    'ctba': 'curitiba',
    'cwb': 'curitiba',
    'bc': 'balneário camboriú',
    'sp': 'são paulo',
    'rj': 'rio de janeiro',
    'bh': 'belo horizonte',
    'poa': 'porto alegre',
    'rec': 'recife',
    'ssalvador': 'salvador',
    'bsb': 'brasília',
    
    # Real estate specific terms
    'imov': 'imóvel',
    'imovel': 'imóvel',
    'cobertura': 'cobertura',
    'duplex': 'duplex',
    'triplex': 'triplex',
    'studio': 'studio',
    'loft': 'loft',
    'sobrado': 'sobrado',
    'chacara': 'chácara',
    'sitio': 'sítio',
    'fazenda': 'fazenda',
    'terreno': 'terreno',
    'lote': 'lote',
    'galpao': 'galpão',
    'comercial': 'comercial',
    'industrial': 'industrial'
}

def expand_abbreviations(text: str) -> str:
    """
    Expand common real estate abbreviations in the search text.
    
    Args:
        text: Original search query text
        
    Returns:
        Text with abbreviations expanded
    """
    if not text:
        return text
        
    # Split into words and process each
    words = text.lower().split()
    expanded_words = []
    
    for word in words:
        # Remove punctuation for matching but preserve it
        clean_word = re.sub(r'[^\w]', '', word)
        
        # Check if the clean word is an abbreviation
        if clean_word in PROPERTY_ABBREVIATIONS:
            # Replace the clean part but preserve any punctuation
            expanded_word = word.replace(clean_word, PROPERTY_ABBREVIATIONS[clean_word])
            expanded_words.append(expanded_word)
        else:
            expanded_words.append(word)
    
    return ' '.join(expanded_words)

def search_properties(query: str, page: int = 1, per_page: int = 12) -> tuple[List[Dict[str, Any]], int]:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Expand abbreviations before parsing
        expanded_query = expand_abbreviations(query)
        
        # Parse natural language query
        conditions, params, search_metadata = parse_search_query(expanded_query)
        
        # Build SQL query
        base_query = """
            SELECT * FROM properties 
            WHERE status = 'active'
        """
        
        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        
        # Count total results
        count_query = """
            SELECT COUNT(*) as total FROM properties 
            WHERE status = 'active'
        """
        
        if conditions:
            count_query += " AND " + " AND ".join(conditions)
        
        cursor = conn.execute(count_query, params)
        total = cursor.fetchone()['total']
        
        # Smart ordering based on search type
        if search_metadata['price_found']:
            if search_metadata['price_direction'] == 'max':
                # For "até 500k", show expensive properties first (closer to limit)
                order_clause = " ORDER BY price DESC, created_at DESC"
            else:
                # For "acima de 200k", show cheaper properties first (closer to minimum)
                order_clause = " ORDER BY price ASC, created_at DESC"
        else:
            # Default ordering by recency
            order_clause = " ORDER BY created_at DESC"
        
        # Get paginated results
        base_query += order_clause + " LIMIT ? OFFSET ?"
        offset = (page - 1) * per_page
        cursor = conn.execute(base_query, params + [per_page, offset])
        
        properties = []
        for row in cursor.fetchall():
            prop = dict(row)
            # Parse JSON fields
            if prop['images']:
                try:
                    prop['images'] = json.loads(prop['images'])
                except json.JSONDecodeError:
                    prop['images'] = []
            else:
                prop['images'] = []
                
            if prop['features']:
                try:
                    prop['features'] = json.loads(prop['features'])
                except json.JSONDecodeError:
                    prop['features'] = []
            else:
                prop['features'] = []
            
            # Format price
            if prop['price']:
                prop['formatted_price'] = format_price(prop['price'])
            
            # Generate slug for SEO-friendly URLs
            prop['slug'] = generate_property_slug(prop)
            
            properties.append(prop)
        
        conn.close()
        return properties, total
        
    except sqlite3.Error as e:
        print(f"Database error in search_properties: {e}")
        # Return empty results on database error
        if 'conn' in locals():
            conn.close()
        return [], 0
    except Exception as e:
        print(f"Unexpected error in search_properties: {e}")
        # Return empty results on any other error
        if 'conn' in locals():
            conn.close()
        return [], 0

def parse_search_query(query: str) -> tuple[List[str], List[Any], dict]:
    conditions = []
    params = []
    query_lower = query.lower()
    
    # Price filters - default to sale properties for price searches
    price_patterns = [
        r'até (\d+)k', r'até (\d+) mil', r'máximo (\d+)k', r'max (\d+)k',
        r'acima de (\d+)k', r'mais de (\d+)k', r'mínimo (\d+)k', r'min (\d+)k'
    ]
    
    price_found = False
    price_direction = None  # 'max' for até/máximo, 'min' for acima/mínimo
    for pattern in price_patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_value = int(match.group(1)) * 1000
            if 'até' in pattern or 'máximo' in pattern or 'max' in pattern:
                conditions.append("price <= ?")
                price_direction = 'max'
            else:
                conditions.append("price >= ?")
                price_direction = 'min'
            params.append(price_value)
            price_found = True
            break
    
    # If price is specified but no transaction type, default to sale
    if price_found and not any(word in query_lower for word in ['venda', 'comprar', 'compra', 'aluguel', 'alugar', 'locação']):
        conditions.append("transaction_type = 'sale'")
    
    # Filter out properties with invalid prices when price filter is used
    if price_found:
        conditions.append("price > 0")
    
    # Property type filters
    type_mapping = {
        'casa': 'Casa', 'casas': 'Casa',
        'apartamento': 'Apartamento', 'apartamentos': 'Apartamento',
        'apto': 'Apartamento', 'aptos': 'Apartamento',
        'terreno': 'Terreno', 'terrenos': 'Terreno',
        'sala': 'Sala', 'salas': 'Sala',
        'loja': 'Loja', 'lojas': 'Loja'
    }
    
    for key, value in type_mapping.items():
        if key in query_lower:
            conditions.append("type = ?")
            params.append(value)
            break
    
    # Transaction type
    if any(word in query_lower for word in ['venda', 'comprar', 'compra']):
        conditions.append("transaction_type = 'sale'")
    elif any(word in query_lower for word in ['aluguel', 'alugar', 'locação']):
        conditions.append("transaction_type = 'rent'")
    
    # Enhanced location filters - prioritize exact neighborhood matches
    location_words = re.findall(r'(?:no|na|em)\s+([a-záêâôõç\s]+?)(?:\s+(?:até|acima|para|com|\d)|$)', query_lower)
    for location in location_words:
        location = location.strip()
        if location:
            # Priority search: exact match > starts with > contains > city match
            conditions.append("""(
                LOWER(neighborhood) = ? OR 
                LOWER(neighborhood) LIKE ? OR 
                LOWER(city) = ? OR
                LOWER(address) LIKE ?
            )""")
            exact_term = location.lower()
            starts_with_term = f"{location.lower()}%"
            address_term = f"%{location.lower()}%"
            params.extend([exact_term, starts_with_term, exact_term, address_term])
    
    # Also handle direct location searches (without prepositions)
    # Look for location names that aren't already captured
    remaining_query = query_lower
    # Remove already processed parts (prices, types, transactions, preposition locations)
    for pattern in [r'até \d+k?', r'acima de \d+k?', r'para (?:venda|aluguel)', r'(?:casa|apartamento|terreno)s?', r'(?:no|na|em)\s+[a-záêâôõç\s]+']:
        remaining_query = re.sub(pattern, '', remaining_query)
    
    remaining_query = remaining_query.strip()
    if remaining_query and len(remaining_query.split()) >= 2:
        # Likely a compound location name (like "jardim carvalho", "vila liane")
        conditions.append("""(
            LOWER(neighborhood) = ? OR 
            LOWER(neighborhood) LIKE ? OR 
            LOWER(city) = ?
        )""")
        exact_term = remaining_query.lower()
        starts_with_term = f"{remaining_query.lower()}%"
        params.extend([exact_term, starts_with_term, exact_term])
    
    # Bedrooms
    bedroom_match = re.search(r'(\d+)\s*(?:quartos?|dormitórios?)', query_lower)
    if bedroom_match:
        bedrooms = int(bedroom_match.group(1))
        conditions.append("bedrooms >= ?")
        params.append(bedrooms)
    
    # Return metadata about the search
    search_metadata = {
        'price_found': price_found,
        'price_direction': price_direction  # 'max' for "até", 'min' for "acima"
    }
    
    return conditions, params, search_metadata

def generate_property_slug(property_data: Dict[str, Any]) -> str:
    """Generate SEO-friendly slug for property"""
    parts = []
    
    # Add property type
    if property_data.get('type'):
        parts.append(property_data['type'].lower())
    
    # Add city
    if property_data.get('city'):
        parts.append(property_data['city'].lower())
    
    # Add neighborhood
    if property_data.get('neighborhood'):
        parts.append(property_data['neighborhood'].lower())
    
    # Add title or create from type and details
    if property_data.get('title'):
        title_slug = slugify(property_data['title'][:50])  # Limit length
        parts.append(title_slug)
    else:
        # Create title from property details
        title_parts = []
        if property_data.get('type'):
            title_parts.append(property_data['type'])
        if property_data.get('bedrooms'):
            title_parts.append(f"{property_data['bedrooms']}-quartos")
        if title_parts:
            parts.append(slugify(' '.join(title_parts)))
    
    # Join parts and add property ID
    slug_base = '-'.join(filter(None, parts))
    return f"{slug_base}-{property_data['id']}" if slug_base else f"imovel-{property_data['id']}"

def sanitize_html_description(html_content: str) -> str:
    """Sanitize HTML content for safe display"""
    if not html_content:
        return ""
    
    # Allowed HTML tags for property descriptions
    allowed_tags = ['p', 'br', 'strong', 'b', 'em', 'i', 'ul', 'ol', 'li', 'h3', 'h4', 'h5', 'h6']
    allowed_attributes = {}
    
    # Clean HTML and allow safe tags
    cleaned = bleach.clean(
        html_content, 
        tags=allowed_tags, 
        attributes=allowed_attributes,
        strip=True
    )
    
    return Markup(cleaned)

def calculate_price_per_sqm(price: float, area: float) -> str:
    """Calculate price per square meter"""
    if not price or not area or area == 0:
        return ""
    
    price_per_sqm = price / area
    return f"R$ {price_per_sqm:,.0f}/m²".replace(",", ".")

def format_price(price: float) -> str:
    # Format with thousands separator
    return f"R$ {price:,.0f}".replace(",", ".")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)