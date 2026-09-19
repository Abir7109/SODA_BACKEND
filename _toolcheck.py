import sys; sys.path.insert(0, 'backend')
import tools
for i, td in enumerate(tools.tools_list[0]['function_declarations']):
    name = td['name']
    params = list(td.get('parameters', {}).get('properties', {}).keys()) if 'parameters' in td else []
    joined = ', '.join(params[:4])
    print(f'{i+1:3d}. {name}({joined})')
print(f'\nTotal: {len(tools.tools_list[0]["function_declarations"])}')
