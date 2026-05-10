import sys, traceback

def transpile_jsx(code):
    i = 0
    n = len(code)
    out = []
    
    def advance(k=1):
        nonlocal i
        i += k
    def peek(k=1):
        return code[i:i+k] if i+k <= n else ''
    def skip_ws():
        nonlocal i
        while i < n and code[i] in ' \t\n\r':
            i += 1
    def parse_tag_name():
        nonlocal i
        start = i
        while i < n and (code[i].isalnum() or code[i] in '_.$'):
            i += 1
        return code[start:i]
    def parse_js_string():
        nonlocal i
        q = code[i]; advance(1); start = i
        while i < n:
            if code[i] == '\\': i += 2
            elif code[i] == q: val = code[start:i]; advance(1); return q + val + q
            else: i += 1
        return q + code[start:i]
    def parse_braced_expr():
        nonlocal i
        if peek() != '{': return None
        advance(1); depth = 1; start = i
        in_sq = in_dq = in_bt = False
        while i < n and depth > 0:
            ch = code[i]
            if ch == '\\': i += 2; continue
            if not in_sq and not in_dq and not in_bt:
                if ch == "'": in_sq = True
                elif ch == '"': in_dq = True
                elif ch == '`': in_bt = True
                elif ch == '{': depth += 1
                elif ch == '}': depth -= 1
            elif in_sq and ch == "'": in_sq = False
            elif in_dq and ch == '"': in_dq = False
            elif in_bt and ch == '`': in_bt = False
            i += 1
        return code[start:i-1]
    
    def parse_attrs():
        nonlocal i
        pairs = []; spread = None
        while i < n:
            skip_ws(); ch = peek()
            if ch == '>': break
            if ch == '/' and i+1 < n and code[i+1] == '>': break
            if ch == '{' and i+1 < n and code[i+1] == '.':
                advance(1); d = 1; s = i
                while i < n and d > 0:
                    if code[i] == '{': d += 1
                    elif code[i] == '}': d -= 1
                    i += 1
                content = code[s:i-1].strip()
                if content.startswith('...'): spread = content[3:].strip()
                continue
            name = parse_tag_name()
            if not name: break
            skip_ws()
            if peek() == '=':
                advance(1); skip_ws()
                vc = peek()
                if vc in '"\'':
                    val = parse_js_string()
                elif vc == '{':
                    expr = parse_braced_expr()
                    val = expr
                else:
                    s = i
                    while i < n and code[i] not in ' \t\n\r>/': i += 1
                    val = code[s:i]
                pairs.append(f'{name}: {val}')
            else:
                pairs.append(f'{name}: true')
        parts = []
        if spread: parts.append('...' + spread)
        parts.extend(pairs)
        return '{' + ', '.join(parts) + '}' if parts else 'null'
    
    def parse_element():
        nonlocal i
        advance(1)
        if peek() == '>':
            advance(1); tag = 'React.Fragment'; tag_str = tag; attrs = 'null'
        else:
            tag = parse_tag_name(); attrs = parse_attrs(); skip_ws()
            if peek(2) == '/>':
                advance(2)
                tag_str = f"'{tag}'" if tag[0].islower() else tag
                return f"React.createElement({tag_str}, {attrs})"
            if peek() == '>': advance(1)
            tag_str = f"'{tag}'" if tag[0].islower() else tag
        
        plain_tag = tag.rsplit('.', 1)[-1]
        children = []
        while i < n:
            if peek(2) == '</':
                save = i; advance(2)
                if plain_tag == 'React.Fragment':
                    if peek() == '>': advance(1); break
                    i = save
                else:
                    ct = parse_tag_name()
                    if ct.rsplit('.', 1)[-1] == plain_tag:
                        skip_ws()
                        if peek() == '>': advance(1); break
                    i = save
            if i >= n: break
            ch = peek()
            if ch == '<' and i+1 < n and (code[i+1].isalpha() or code[i+1] == '>'):
                children.append(parse_element()); continue
            if ch == '{':
                expr = parse_braced_expr()
                if expr is not None and not expr.strip().startswith('/*'):
                    expr_transpiled = transpile_jsx(expr)
                    children.append(expr_transpiled)
                continue
            s = i
            while i < n and code[i] not in '<{': i += 1
            txt = code[s:i]
            if txt.strip():
                esc = txt.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
                children.append(f"'{esc}'")
        
        if children:
            return f"React.createElement({tag_str}, {attrs}, {', '.join(children)})"
        return f"React.createElement({tag_str}, {attrs})"
    
    in_sq = in_dq = in_bt = False  # string context tracking
    while i < n:
        c = code[i]
        
        # Track string context
        if not in_sq and not in_dq and not in_bt:
            if c == "'" and (i == 0 or code[i-1] != '\\'): in_sq = True
            elif c == '"' and (i == 0 or code[i-1] != '\\'): in_dq = True
            elif c == '`' and (i == 0 or code[i-1] != '\\'): in_bt = True
        elif in_sq and c == "'" and (i == 0 or code[i-1] != '\\'): in_sq = False
        elif in_dq and c == '"' and (i == 0 or code[i-1] != '\\'): in_dq = False
        elif in_bt and c == '`' and (i == 0 or code[i-1] != '\\'): in_bt = False
        
        # Only parse JSX outside of strings
        if not in_sq and not in_dq and not in_bt and c == '<' and i+1 < n:
            nxt = code[i+1]
            # Check if this is a JSX tag or a comparison operator
            # < is JSX only if preceded by =, (, [, {, :, ,, &&, ||, ?, !, =>, or start of line
            is_jsx = False
            if nxt.isalpha() or nxt == '>' or nxt == '/':
                # Check preceding context
                if i == 0:
                    is_jsx = True
                else:
                    # Find last non-whitespace char before <
                    j = i - 1
                    while j >= 0 and code[j] in ' \t\n\r':
                        j -= 1
                    if j < 0:
                        is_jsx = True
                    else:
                        pc = code[j]
                        # < is JSX if preceded by: = ( [ { : , & | ? ! or > (for =>)
                        if pc in '=([{:,&|?!':
                            is_jsx = True
                        elif pc == '>' and j > 0 and code[j-1] == '=':
                            is_jsx = True  # => 
                        elif pc == '>' and j > 0:
                            # Check if it's -> or just >
                            is_jsx = True
                        # NOT JSX if preceded by identifier, digit, ), ], or "
                        elif pc.isalnum() or pc == ')' or pc == ']':
                            is_jsx = False
                        else:
                            is_jsx = True
            if is_jsx:
                save_i = i
                try:
                    result = parse_element()
                    out.append(result)
                    continue
                except Exception:
                    i = save_i
                    out.append(c)
                    i += 1
            else:
                out.append(c)
                i += 1
            continue
        out.append(c)
        i += 1
    
    return ''.join(out)


if __name__ == '__main__':
    html_path = sys.argv[1]
    output_path = sys.argv[2]
    
    with open(html_path, 'r') as f:
        html = f.read()
    
    # Find Babel script block
    babel_start = html.find('<script type="text/babel" data-presets="react">')
    if babel_start < 0:
        print("ERROR: Babel script not found")
        sys.exit(1)
    
    code_start = html.find('>', babel_start) + 1
    babel_end_marker = html.find('</script>', code_start)
    babel_end = babel_end_marker + len('</script>')
    
    jsx_code = html[code_start:babel_end_marker]
    print(f"JSX code: {len(jsx_code)} chars")
    
    try:
        transpiled = transpile_jsx(jsx_code)
        print(f"Transpiled: {len(transpiled)} chars")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Build new HTML - properly replace the babel script block
    before = html[:babel_start]
    after = html[babel_end:]  # after the closing </script>
    
    new_script = '<script>\n' + transpiled + '\n</script>'
    new_html = before + new_script + after
    
    # Remove Babel standalone CDN
    new_html = new_html.replace(
        '<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>\n',
        ''
    )
    
    print(f"New HTML: {len(new_html)} chars")
    
    with open(output_path, 'w') as f:
        f.write(new_html)
    
    # Verify
    sc_open = new_html.count('<script')
    sc_close = new_html.count('</script>')
    print(f"Script tags: {sc_open} open, {sc_close} close => {'BALANCED' if sc_open == sc_close else 'UNBALANCED'}")
    print("Done!")
