from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import json

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
        "current_page": page,
        "total_pages": total_pages,
        "total": total
    })

def search_properties(query: str, page: int = 1, per_page: int = 12) -> tuple[List[Dict[str, Any]], int]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Parse natural language query
    conditions, params = parse_search_query(query)
    
    # Build SQL query
    base_query = """
        SELECT * FROM properties 
        WHERE status = 'active'
    """
    
    if conditions:
        base_query += " AND " + " AND ".join(conditions)
    
    # Count total results
    count_query = f"SELECT COUNT(*) as total FROM ({base_query})"
    cursor = conn.execute(count_query, params)
    total = cursor.fetchone()['total']
    
    # Get paginated results
    base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    offset = (page - 1) * per_page
    cursor = conn.execute(base_query, params + [per_page, offset])
    
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
        
        properties.append(prop)
    
    conn.close()
    return properties, total

def parse_search_query(query: str) -> tuple[List[str], List[Any]]:
    conditions = []
    params = []
    query_lower = query.lower()
    
    # Price filters
    price_patterns = [
        r'até (\d+)k', r'até (\d+) mil', r'máximo (\d+)k', r'max (\d+)k',
        r'acima de (\d+)k', r'mais de (\d+)k', r'mínimo (\d+)k', r'min (\d+)k'
    ]
    
    for pattern in price_patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_value = int(match.group(1)) * 1000
            if 'até' in pattern or 'máximo' in pattern or 'max' in pattern:
                conditions.append("price <= ?")
            else:
                conditions.append("price >= ?")
            params.append(price_value)
    
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
    
    # Location filters (neighborhood, city)
    location_words = re.findall(r'(?:no|na|em)\s+([a-záêâôõç\s]+?)(?:\s|$)', query_lower)
    for location in location_words:
        location = location.strip()
        if location:
            conditions.append("(LOWER(neighborhood) LIKE ? OR LOWER(city) LIKE ? OR LOWER(address) LIKE ?)")
            like_term = f"%{location}%"
            params.extend([like_term, like_term, like_term])
    
    # Bedrooms
    bedroom_match = re.search(r'(\d+)\s*(?:quartos?|dormitórios?)', query_lower)
    if bedroom_match:
        bedrooms = int(bedroom_match.group(1))
        conditions.append("bedrooms >= ?")
        params.append(bedrooms)
    
    return conditions, params

def format_price(price: float) -> str:
    if price >= 1_000_000:
        return f"R$ {price/1_000_000:.1f}M"
    elif price >= 1_000:
        return f"R$ {price/1_000:.0f}k"
    else:
        return f"R$ {price:,.0f}"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)