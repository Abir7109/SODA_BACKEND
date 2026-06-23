import sys
sys.path.insert(0, r'D:\soda-main-master\soda-main-master\backend')
from local_agent import _dispatch, LOCAL_TOOLS

print("tools with 'window':", [t for t in LOCAL_TOOLS if 'window' in t])
print()

# Test window_list
r = _dispatch('window_list', {})
print("window_list returned:", r.get('success'))
if r.get('success'):
    print("Total windows:", len(r.get('windows', [])))
    for w in r.get('windows', [])[:15]:
        vis = 'VIS' if w.get('visible') else 'hid'
        print(f"  [{vis}] {w['title'][:70]}")
else:
    print("ERROR:", r.get('error'))
print()

# Test window_manage
r = _dispatch('window_manage', {'title': 'OpenCode', 'action': 'minimize'})
print("window_manage minimize:", r)
