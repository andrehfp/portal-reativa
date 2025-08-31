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
    
    # Generate filter data for the UI
    active_filters = extract_active_filters(q)
    filter_suggestions = generate_filter_suggestions(q, properties, total)
    
    return templates.TemplateResponse("components/property_grid.html", {
        "request": request,
        "properties": properties,
        "query": q,
        "current_page": page,
        "total_pages": total_pages,
        "total": total,
        "active_filters": active_filters,
        "filter_suggestions": filter_suggestions
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

def extract_active_filters(query: str) -> List[Dict[str, str]]:
    """
    Extract active filters from the search query for display as pills.
    
    Returns:
        List of filter dictionaries with type, value, label, and remove_query keys
    """
    if not query:
        return []
    
    active_filters = []
    query_lower = query.lower()
    expanded_query = expand_abbreviations(query_lower)
    
    # Price filters
    price_patterns = [
        (r'até (\d+)k', lambda x: f"Até R$ {int(x) * 1000:,}".replace(",", "."), 'price'),
        (r'acima de (\d+)k', lambda x: f"Acima de R$ {int(x) * 1000:,}".replace(",", "."), 'price'),
        (r'até (\d+) mil', lambda x: f"Até R$ {int(x) * 1000:,}".replace(",", "."), 'price'),
        (r'acima de (\d+) mil', lambda x: f"Acima de R$ {int(x) * 1000:,}".replace(",", "."), 'price'),
        (r'até (\d{3,})', lambda x: f"Até R$ {int(x):,}".replace(",", "."), 'price'),
        (r'acima de (\d{3,})', lambda x: f"Acima de R$ {int(x):,}".replace(",", "."), 'price'),
    ]
    
    for pattern, label_func, filter_type in price_patterns:
        match = re.search(pattern, expanded_query)
        if match:
            label = label_func(match.group(1))
            # Create query without this price filter for removal
            remove_query = re.sub(pattern, '', expanded_query).strip()
            remove_query = re.sub(r'\s+', ' ', remove_query)  # Clean up extra spaces
            
            active_filters.append({
                'type': filter_type,
                'value': match.group(0),
                'label': label,
                'remove_query': remove_query if remove_query != expanded_query else ''
            })
            break
    
    # Property type filters
    type_mapping = {
        'casa': 'Casa', 'casas': 'Casa',
        'apartamento': 'Apartamento', 'apartamentos': 'Apartamento',
        'apto': 'Apartamento', 'aptos': 'Apartamento',
        'terreno': 'Terreno', 'terrenos': 'Terreno',
        'sala': 'Sala', 'salas': 'Sala',
        'loja': 'Loja', 'lojas': 'Loja',
        'kitnet': 'Kitnet'
    }
    
    for key, value in type_mapping.items():
        if key in expanded_query:
            # Create query without this property type for removal
            remove_query = expanded_query.replace(key, '').strip()
            remove_query = re.sub(r'\s+', ' ', remove_query)  # Clean up extra spaces
            
            active_filters.append({
                'type': 'property_type',
                'value': key,
                'label': value,
                'remove_query': remove_query if remove_query != expanded_query else ''
            })
            break
    
    # Location filters
    location_matches = re.findall(r'(?:no|na|em)\s+([a-záêâôõç\s]+?)(?:\s+(?:até|acima|para|com|de\s+[a-z]+|\d)|$)', expanded_query)
    for location in location_matches:
        location = location.strip()
        if location:
            # Create query without this location for removal
            location_pattern = f'(?:no|na|em)\\s+{re.escape(location)}'
            remove_query = re.sub(location_pattern, '', expanded_query, flags=re.IGNORECASE).strip()
            remove_query = re.sub(r'\s+', ' ', remove_query)  # Clean up extra spaces
            
            active_filters.append({
                'type': 'location',
                'value': location,
                'label': location.title(),
                'remove_query': remove_query if remove_query != expanded_query else ''
            })
    
    # Bedrooms filter
    bedroom_match = re.search(r'(\d+)\s*(?:quartos?|dormitórios?)', expanded_query)
    if bedroom_match:
        bedrooms = bedroom_match.group(1)
        label = f"{bedrooms} quarto{'s' if int(bedrooms) > 1 else ''}"
        
        # Create query without this bedroom filter for removal
        bedroom_pattern = r'\d+\s*(?:quartos?|dormitórios?)'
        remove_query = re.sub(bedroom_pattern, '', expanded_query).strip()
        remove_query = re.sub(r'\s+', ' ', remove_query)  # Clean up extra spaces
        
        active_filters.append({
            'type': 'bedrooms',
            'value': bedrooms,
            'label': label,
            'remove_query': remove_query if remove_query != expanded_query else ''
        })
    
    # Transaction type filters
    if any(phrase in expanded_query for phrase in ['para venda', 'para vender', 'a venda', 'venda']):
        remove_phrases = ['para venda', 'para vender', 'a venda', 'venda']
        remove_query = expanded_query
        for phrase in remove_phrases:
            remove_query = remove_query.replace(phrase, '')
        remove_query = re.sub(r'\s+', ' ', remove_query.strip())
        
        active_filters.append({
            'type': 'transaction_type',
            'value': 'sale',
            'label': 'Venda',
            'remove_query': remove_query if remove_query != expanded_query else ''
        })
    elif any(phrase in expanded_query for phrase in ['para alugar', 'para aluguel', 'aluguel', 'alugar']):
        remove_phrases = ['para alugar', 'para aluguel', 'aluguel', 'alugar']
        remove_query = expanded_query
        for phrase in remove_phrases:
            remove_query = remove_query.replace(phrase, '')
        remove_query = re.sub(r'\s+', ' ', remove_query.strip())
        
        active_filters.append({
            'type': 'transaction_type',
            'value': 'rent',
            'label': 'Aluguel',
            'remove_query': remove_query if remove_query != expanded_query else ''
        })
    
    return active_filters


def generate_filter_suggestions(query: str, properties: List[Dict], total_results: int) -> List[Dict[str, Any]]:
    """
    Generate contextual filter suggestions based on the current search and results.
    
    Returns:
        List of suggestion dictionaries with type, value, label, count, and add_query keys
    """
    if not query or total_results == 0:
        return []
    
    suggestions = []
    query_lower = query.lower()
    expanded_query = expand_abbreviations(query_lower)
    
    # Get database connection to run suggestion queries
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Parse current query to understand what's already filtered
        current_conditions, current_params, search_metadata = parse_search_query(expanded_query)
        
        base_query = """
            SELECT COUNT(*) as count FROM properties 
            WHERE status = 'active'
        """
        
        if current_conditions:
            base_query += " AND " + " AND ".join(current_conditions)
        
        # Suggest price ranges if no price filter exists
        if not search_metadata.get('price_found'):
            price_suggestions = [
                ('até 300k', 'Até R$ 300k', 300000, '<='),
                ('até 500k', 'Até R$ 500k', 500000, '<='),
                ('até 1 milhão', 'Até R$ 1M', 1000000, '<='),
                ('acima de 200k', 'Acima de R$ 200k', 200000, '>='),
                ('acima de 500k', 'Acima de R$ 500k', 500000, '>='),
            ]
            
            for value, label, price_num, operator in price_suggestions:
                price_query = base_query + f" AND price {operator} ? AND price > 0"
                cursor = conn.execute(price_query, current_params + [price_num])
                count = cursor.fetchone()['count']
                
                if count > 0:
                    add_query = f"{query} {value}".strip()
                    suggestions.append({
                        'type': 'price',
                        'value': value,
                        'label': label,
                        'count': count,
                        'add_query': add_query
                    })
        
        # Suggest property types if no type filter exists
        has_property_type = any(ptype in expanded_query for ptype in ['casa', 'apartamento', 'terreno', 'sala', 'loja', 'kitnet'])
        if not has_property_type:
            type_suggestions = [
                ('apartamento', 'Apartamento', 'Apartamento'),
                ('casa', 'Casa', 'Casa'),
                ('terreno', 'Terreno', 'Terreno'),
            ]
            
            for value, label, db_type in type_suggestions:
                type_query = base_query + " AND type = ?"
                cursor = conn.execute(type_query, current_params + [db_type])
                count = cursor.fetchone()['count']
                
                if count > 0:
                    add_query = f"{query} {value}".strip()
                    suggestions.append({
                        'type': 'property_type',
                        'value': value,
                        'label': label,
                        'count': count,
                        'add_query': add_query
                    })
        
        # Suggest bedrooms if no bedroom filter exists
        has_bedrooms = re.search(r'\d+\s*(?:quartos?|dormitórios?)', expanded_query)
        if not has_bedrooms:
            bedroom_suggestions = [
                ('2 quartos', '2 quartos', 2),
                ('3 quartos', '3 quartos', 3),
                ('4 quartos', '4+ quartos', 4),
            ]
            
            for value, label, bedroom_count in bedroom_suggestions:
                bedroom_query = base_query + " AND bedrooms >= ?"
                cursor = conn.execute(bedroom_query, current_params + [bedroom_count])
                count = cursor.fetchone()['count']
                
                if count > 0:
                    add_query = f"{query} {value}".strip()
                    suggestions.append({
                        'type': 'bedrooms',
                        'value': value,
                        'label': label,
                        'count': count,
                        'add_query': add_query
                    })
        
        # Suggest popular neighborhoods based on current results
        has_location = re.search(r'(?:no|na|em)\s+([a-záêâôõç\s]+)', expanded_query)
        if not has_location and properties:
            # Get top neighborhoods from current results
            neighborhoods = {}
            for prop in properties[:10]:  # Check first 10 properties
                if prop.get('neighborhood'):
                    neighborhood = prop['neighborhood'].lower()
                    neighborhoods[neighborhood] = neighborhoods.get(neighborhood, 0) + 1
            
            # Suggest top neighborhoods
            for neighborhood, _ in sorted(neighborhoods.items(), key=lambda x: x[1], reverse=True)[:3]:
                neighborhood_query = base_query + " AND LOWER(neighborhood) LIKE ?"
                cursor = conn.execute(neighborhood_query, current_params + [f"%{neighborhood}%"])
                count = cursor.fetchone()['count']
                
                if count > 0:
                    add_query = f"{query} no {neighborhood}".strip()
                    suggestions.append({
                        'type': 'location',
                        'value': f"no {neighborhood}",
                        'label': neighborhood.title(),
                        'count': count,
                        'add_query': add_query
                    })
        
        conn.close()
        
        # Sort suggestions by count (most results first) and limit to 5
        suggestions.sort(key=lambda x: x['count'], reverse=True)
        return suggestions[:5]
        
    except sqlite3.Error as e:
        print(f"Database error in generate_filter_suggestions: {e}")
        if 'conn' in locals():
            conn.close()
        return []
    except Exception as e:
        print(f"Error generating filter suggestions: {e}")
        if 'conn' in locals():
            conn.close()
        return []


def parse_search_query(query: str) -> tuple[List[str], List[Any], dict]:
    conditions = []
    params = []
    query_lower = query.lower()
    
    # Expand abbreviations first and work with expanded query
    expanded_query = expand_abbreviations(query_lower)
    
    # Enhanced price parsing - handle various price formats
    # IMPORTANT: Order matters! More specific patterns (k, mil, milhões) must come BEFORE general patterns
    price_patterns = [
        # Handle k format (thousands)
        (r'até (\d+)k', lambda x: int(x) * 1000),  # até 200k = 200000
        (r'acima de (\d+)k', lambda x: int(x) * 1000),  # acima de 300k = 300000
        (r'máximo (\d+)k', lambda x: int(x) * 1000),  # máximo 500k
        (r'mínimo (\d+)k', lambda x: int(x) * 1000),  # mínimo 100k
        
        # Handle mil format (thousands)
        (r'até (\d+) mil', lambda x: int(x) * 1000),  # até 300 mil = 300000
        (r'acima de (\d+) mil', lambda x: int(x) * 1000),  # acima de 200 mil = 200000
        
        # Handle milhões format (millions)
        (r'até (\d+) milhões?', lambda x: int(x) * 1000000),  # até 2 milhões = 2000000
        (r'acima de (\d+) milhões?', lambda x: int(x) * 1000000),  # acima de 1 milhão = 1000000
        
        # Handle raw numbers (likely rent prices) - MUST BE LAST
        (r'até (\d{3,})', lambda x: int(x)),  # até 1500, até 2500 (raw values)
        (r'acima de (\d{3,})', lambda x: int(x)),  # acima de 1500 (raw values)
    ]
    
    price_found = False
    price_direction = None  # 'max' for até/máximo, 'min' for acima/mínimo
    
    for pattern, price_converter in price_patterns:
        match = re.search(pattern, expanded_query)
        if match:
            price_value = price_converter(match.group(1))
            
            if 'até' in pattern or 'máximo' in pattern or 'max' in pattern:
                conditions.append("price <= ?")
                price_direction = 'max'
            else:
                conditions.append("price >= ?")
                price_direction = 'min'
            params.append(price_value)
            price_found = True
            break
    
    # Property type filters - use expanded query
    type_mapping = {
        'casa': 'Casa', 'casas': 'Casa',
        'apartamento': 'Apartamento', 'apartamentos': 'Apartamento',
        'apto': 'Apartamento', 'aptos': 'Apartamento',
        'terreno': 'Terreno', 'terrenos': 'Terreno',
        'sala': 'Sala', 'salas': 'Sala',
        'loja': 'Loja', 'lojas': 'Loja',
        'kitnet': 'Kitnet'
    }
    
    for key, value in type_mapping.items():
        if key in expanded_query:
            conditions.append("type = ?")
            params.append(value)
            break
    
    # Enhanced transaction type parsing - only add once
    transaction_type_set = False
    if any(phrase in expanded_query for phrase in ['para venda', 'para vender', 'a venda', 'venda', 'comprar', 'compra']):
        conditions.append("transaction_type = 'sale'")
        transaction_type_set = True
    elif any(phrase in expanded_query for phrase in ['para alugar', 'para aluguel', 'aluguel', 'alugar', 'locação']):
        conditions.append("transaction_type = 'rent'")
        transaction_type_set = True
    
    # If price is specified but no transaction type, default to sale
    if price_found and not transaction_type_set:
        conditions.append("transaction_type = 'sale'")
    
    # Filter out properties with invalid prices when price filter is used
    if price_found:
        conditions.append("price > 0")
    
    # Enhanced location parsing - handle compound locations better
    # Parse the entire query for location information
    all_location_terms = []
    
    # Extract locations with prepositions (no|na|em)
    location_matches = re.findall(r'(?:no|na|em)\s+([a-záêâôõç\s]+?)(?:\s+(?:até|acima|para|com|de\s+[a-z]+|\d)|$)', expanded_query)
    for location in location_matches:
        all_location_terms.append(location.strip())
    
    # Extract compound locations like "centro de ponta grossa"
    compound_matches = re.findall(r'([a-záêâôõç]+)\s+de\s+([a-záêâôõç\s]+)', expanded_query)
    for neighborhood, city in compound_matches:
        # Add the compound location as a single term
        all_location_terms.append(f"{neighborhood} de {city}")
    
    # Process all location terms and create a single comprehensive condition
    if all_location_terms:
        location_conditions = []
        location_params = []
        
        for location in all_location_terms:
            if ' de ' in location:
                # Handle compound locations (e.g., "centro de ponta grossa")
                parts = location.split(' de ')
                neighborhood = parts[0].strip()
                city = parts[1].strip()
                
                # Add specific neighborhood + city condition
                location_conditions.append("(LOWER(neighborhood) LIKE ? AND LOWER(city) LIKE ?)")
                location_params.extend([f"%{neighborhood}%", f"%{city}%"])
                
                # Also add individual neighborhood and city conditions as fallback
                location_conditions.extend([
                    "LOWER(neighborhood) LIKE ?",
                    "LOWER(city) LIKE ?"
                ])
                location_params.extend([f"%{neighborhood}%", f"%{city}%"])
            else:
                # Single location term - search in all location fields
                location_conditions.extend([
                    "LOWER(neighborhood) = ?",
                    "LOWER(neighborhood) LIKE ?", 
                    "LOWER(city) = ?",
                    "LOWER(address) LIKE ?"
                ])
                exact_term = location.lower()
                starts_with_term = f"{location.lower()}%"
                address_term = f"%{location.lower()}%"
                location_params.extend([exact_term, starts_with_term, exact_term, address_term])
        
        # Combine all location conditions with OR
        if location_conditions:
            combined_location_condition = "(" + " OR ".join(location_conditions) + ")"
            conditions.append(combined_location_condition)
            params.extend(location_params)
    
    # Bedrooms parsing
    bedroom_match = re.search(r'(\d+)\s*(?:quartos?|dormitórios?)', expanded_query)
    if bedroom_match:
        bedrooms = int(bedroom_match.group(1))
        conditions.append("bedrooms >= ?")
        params.append(bedrooms)
    
    # Return metadata about the search
    search_metadata = {
        'price_found': price_found,
        'price_direction': price_direction,
        'expanded_query': expanded_query
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