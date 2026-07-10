import sys, re

path = r'D:\soda-main-master\soda-main-master\backend\tools.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Find the android comment header
header_marker = '# ── Android Agent Tool Definitions ──'
defs_start = text.find(header_marker)
if defs_start == -1:
    print('ERROR: android definitions header not found')
    sys.exit(1)

# Find 'tools_list' after the definitions
tools_list_marker = '\ntools_list = ['
defs_end = text.find(tools_list_marker, defs_start)
if defs_end == -1:
    print('ERROR: tools_list not found after android defs')
    sys.exit(1)

# Remove from header to before tools_list
before = text[:defs_start]
# Keep the newline before tools_list
after = text[defs_end+1:]
text = before + '\n' + after

# Now remove android entries from the tools_list body
# Find the android section comment in tools_list
list_header_marker = '# ── Android Agent Tools ──'
list_start = text.find(list_header_marker)
if list_start == -1:
    print('ERROR: android list header not found')
    sys.exit(1)

# Find the end of the list (closing ]}])
list_close = text.find(']}]', list_start)
if list_close == -1:
    print('ERROR: list closing not found')
    sys.exit(1)

# Remove from android list header to before the closing
before_list = text[:list_start]
# Keep the newline before the closing bracket
# Find the last newline before ]}]
nl_before_close = text.rfind('\n', list_start, list_close)
after_list = text[nl_before_close:]
text = before_list + after_list

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

print('Done - android tools removed')
