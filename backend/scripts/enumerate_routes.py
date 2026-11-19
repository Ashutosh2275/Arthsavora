import re

with open('../apps/web/src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to capture path and element
route_matches = re.finditer(r'<Route\s+path=["\']([^"\']+)["\']\s+element=\{([\s\S]*?)\}\s*/>', content)

routes = []
for m in route_matches:
    path = m.group(1)
    element_raw = m.group(2)
    # Extract inner component
    inner_comps = re.findall(r'<([A-Z][a-zA-Z0-9]+)', element_raw)
    page_comp = [c for c in inner_comps if c not in ('ProtectedRoute', 'AppLayout', 'Navigate')]
    comp_name = page_comp[0] if page_comp else ('Navigate' if 'Navigate' in element_raw else 'Unknown')
    is_protected = 'ProtectedRoute' in element_raw
    routes.append((path, comp_name, is_protected, element_raw.strip()))

print(f"Total Routes defined in App.tsx: {len(routes)}\n")
print(f"{'Path':<24} {'Component':<22} {'Protected':<12}")
print("-" * 60)
for path, comp, prot, _ in routes:
    print(f"{path:<24} {comp:<22} {str(prot):<12}")
